import sys
from pathlib import Path

from fastapi.testclient import TestClient

IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"
sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.main import app  # noqa: E402


client = TestClient(app)


def test_witness_and_gossip_read_only_apis():
    witnesses = client.get("/transparency/witnesses")
    assert witnesses.status_code == 200
    witness_body = witnesses.json()
    assert set(witness_body) == {"witnesses", "count"}
    assert witness_body["count"] == len(witness_body["witnesses"])
    witness_id = witness_body["witnesses"][0]["witness_id"]
    identity = client.get(
        f"/transparency/witnesses/{witness_id}/.well-known/gap-witness.json"
    )
    assert identity.status_code == 200
    assert identity.json()["gap_version"] == "0.13.0"
    statements = client.get("/transparency/witness-statements")
    assert statements.status_code == 200
    statement_body = statements.json()
    assert set(statement_body) == {"witness_statements", "count"}
    assert statement_body["count"] == len(statement_body["witness_statements"])
    assert statement_body["witness_statements"]
    quorum = client.get("/transparency/witness-quorum").json()
    assert quorum["quorum_met"] is True
    gossip_response = client.get("/transparency/gossip/status")
    assert gossip_response.status_code == 200
    gossip_body = gossip_response.json()
    assert set(gossip_body) == {"status", "observation_count"}
    assert gossip_body["status"]["checkpoint_gossip_consistent"] is True
    observations_response = client.get("/transparency/gossip/observations")
    assert observations_response.status_code == 200
    observation_body = observations_response.json()
    assert set(observation_body) == {"observations", "count"}
    assert observation_body["count"] == len(observation_body["observations"])
    assert gossip_body["observation_count"] == observation_body["count"]
    assert observation_body["observations"]
    first = observation_body["observations"][0]
    assert isinstance(first["witness_statements"], list)
    assert "consistency_proof_to_previous" in first
    assert "previous_signed_tree_head" in first
    payload = first["signed_tree_head"]["payload"]
    assert {
        "tree_head_id",
        "log_id",
        "log_name",
        "tree_size",
        "root_hash",
        "timestamp",
    } <= payload.keys()
    encoded = observations_response.text
    assert "private_key" not in encoded
    assert "runtime/" not in encoded


def test_credential_verification_requires_witness_and_gossip():
    generated = client.post(
        "/generations/create",
        json={
            "provider_id": "gap-demo-provider",
            "account_reference": "private-test-account",
            "prompt": "witness policy test",
            "retention_days": 30,
        },
    )
    assert generated.status_code == 201
    verified = client.post(
        "/credentials/verify", json={"credential": generated.json()["credential"]}
    ).json()
    assert verified["cryptographic_valid"] is True
    assert verified["transparency_verified"] is True
    assert verified["witness_quorum_met"] is True
    assert verified["checkpoint_gossip_consistent"] is True
    assert verified["split_view_detected"] is False
    assert verified["witness_equivocation_detected"] is False
    assert verified["valid"] is True


def test_no_public_signing_or_import_routes():
    assert client.post(
        "/transparency/witness-statements/issue", json={}
    ).status_code in {404, 405}
    assert client.post("/transparency/gossip/import", json={}).status_code in {
        404,
        405,
    }
