import sys
from pathlib import Path

from fastapi.testclient import TestClient


IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"
sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.main import app  # noqa: E402


client = TestClient(app)


def test_transparency_read_apis_and_no_append_route() -> None:
    summary = client.get("/transparency/log")
    assert summary.status_code == 200
    assert summary.json()["entry_count"] >= 1
    identity = client.get("/transparency/log/.well-known/gap-transparency.json").json()
    assert identity["tree_algorithm"] == "GAP-RFC6962-SHA256-v1"
    entries = client.get("/transparency/entries").json()
    assert entries
    assert "private_key_path" not in str(entries)
    assert "contact_reference" not in str(entries)
    entry_id = entries[0]["entry_id"]
    assert client.get(f"/transparency/entries/{entry_id}").status_code == 200
    assert client.get("/transparency/entries/unknown").status_code == 404
    assert client.post("/transparency/entries", json={}).status_code == 405


def test_tree_head_and_stateless_inclusion_verification() -> None:
    entries = client.get("/transparency/entries").json()
    entry_id = entries[0]["entry_id"]
    entry = client.get(f"/transparency/entries/{entry_id}").json()
    head = client.get("/transparency/tree-head").json()
    proof = client.get(f"/transparency/entries/{entry_id}/inclusion-proof").json()
    before = client.get("/transparency/log").json()["entry_count"]
    result = client.post(
        "/transparency/verify-inclusion",
        json={"entry": entry, "tree_head": head, "proof": proof},
    )
    assert result.status_code == 200
    assert result.json()["valid"] is True
    assert client.get("/transparency/log").json()["entry_count"] == before
    entry["object_digest"] = "0" * 64
    assert (
        client.post(
            "/transparency/verify-inclusion",
            json={"entry": entry, "tree_head": head, "proof": proof},
        ).json()["valid"]
        is False
    )


def test_verification_and_trust_responses_expose_transparency() -> None:
    trust = client.get("/providers/gap-demo-provider/trust").json()
    assert trust["transparency_verified"] is True
    assert trust["transparency_sources"][0]["transparency_entry_id"]
    registry = client.get("/trust-registry").json()
    assert all("transparency_verified" in entry for entry in registry)
    health = client.get("/health").json()
    assert health["version"] == "0.13.0"
    assert health["transparency_log_loaded"] is True
