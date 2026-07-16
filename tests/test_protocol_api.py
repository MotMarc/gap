import base64
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.main import app  # noqa: E402


client = TestClient(app)


def issue_test_credential() -> dict:
    artifact = base64.b64encode(
        b"GAP generated artifact",
    ).decode("utf-8")

    response = client.post(
        "/credentials/issue",
        json={
            "provider_id": "gap-demo-provider",
            "model_id": "demo-model-v1",
            "media_type": "text/plain",
            "artifact_base64": artifact,
            "account_reference": "user-001",
            "prompt": "Generate a GAP test artifact.",
        },
    )

    assert response.status_code == 201

    return response.json()


def create_valid_authorisation(
    provider_id: str = "gap-demo-provider",
    purpose: str = "criminal-investigation",
) -> dict:
    current_time = datetime.now(timezone.utc)

    return {
        "authorisation_id": "court-order-001",
        "investigator_reference": "investigator-001",
        "issuing_authority": "Crown Court",
        "jurisdiction": "GB",
        "purpose": purpose,
        "issued_at": (current_time - timedelta(minutes=5)).isoformat(),
        "expires_at": (current_time + timedelta(hours=1)).isoformat(),
        "provider_id": provider_id,
    }


def test_list_providers() -> None:
    response = client.get("/providers")

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1
    assert body[0]["provider_id"] == "gap-demo-provider"


def test_provider_identity_endpoint() -> None:
    response = client.get("/providers/gap-demo-provider/.well-known/gap.json")

    assert response.status_code == 200

    body = response.json()

    assert body["provider_id"] == "gap-demo-provider"
    assert body["provider_name"] == "GAP Demo Provider"
    assert len(body["keys"]) == 1
    assert body["keys"][0]["algorithm"] == "Ed25519"


def test_unknown_provider_identity_returns_404() -> None:
    response = client.get("/providers/unknown-provider/.well-known/gap.json")

    assert response.status_code == 404


def test_issue_generation_credential() -> None:
    credential = issue_test_credential()

    assert credential["payload"]["provider"]["provider_id"] == ("gap-demo-provider")
    assert credential["payload"]["model"]["model_id"] == "demo-model-v1"
    assert credential["proof"]["type"] == "Ed25519"
    assert credential["proof"]["key_id"] == "key-2026-01"


def test_unknown_provider_cannot_issue_credential() -> None:
    artifact = base64.b64encode(
        b"GAP generated artifact",
    ).decode("utf-8")

    response = client.post(
        "/credentials/issue",
        json={
            "provider_id": "unknown-provider",
            "model_id": "demo-model-v1",
            "media_type": "text/plain",
            "artifact_base64": artifact,
            "account_reference": "user-001",
            "prompt": "Generate a GAP test artifact.",
        },
    )

    assert response.status_code == 404


def test_verify_generation_credential() -> None:
    credential = issue_test_credential()

    response = client.post(
        "/credentials/verify",
        json={
            "credential": credential,
        },
    )

    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_tampered_credential_is_invalid() -> None:
    credential = issue_test_credential()

    credential["payload"]["model"]["model_id"] = "tampered-model"

    response = client.post(
        "/credentials/verify",
        json={
            "credential": credential,
        },
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_invalid_base64_is_rejected() -> None:
    response = client.post(
        "/credentials/issue",
        json={
            "provider_id": "gap-demo-provider",
            "model_id": "demo-model-v1",
            "media_type": "text/plain",
            "artifact_base64": "not valid base64!",
            "account_reference": "user-001",
            "prompt": "Generate a GAP test artifact.",
        },
    )

    assert response.status_code == 422


def test_private_attribution_record_can_be_disclosed() -> None:
    credential = issue_test_credential()
    generation_id = credential["payload"]["generation"]["generation_id"]

    response = client.post(
        "/disclosures/resolve",
        json={
            "generation_id": generation_id,
            "authorisation": create_valid_authorisation(),
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["generation_id"] == generation_id
    assert body["provider_id"] == "gap-demo-provider"
    assert body["account_reference"] == "user-001"
    assert len(body["prompt_hash"]) == 64


def test_unknown_generation_id_cannot_be_disclosed() -> None:
    response = client.post(
        "/disclosures/resolve",
        json={
            "generation_id": "gid_" + "f" * 64,
            "authorisation": create_valid_authorisation(),
        },
    )

    assert response.status_code == 404


def test_expired_authorisation_is_denied() -> None:
    credential = issue_test_credential()
    generation_id = credential["payload"]["generation"]["generation_id"]

    current_time = datetime.now(timezone.utc)

    authorisation = create_valid_authorisation()
    authorisation["issued_at"] = (current_time - timedelta(hours=2)).isoformat()
    authorisation["expires_at"] = (current_time - timedelta(hours=1)).isoformat()

    response = client.post(
        "/disclosures/resolve",
        json={
            "generation_id": generation_id,
            "authorisation": authorisation,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The authorisation has expired."


def test_future_authorisation_is_denied() -> None:
    credential = issue_test_credential()
    generation_id = credential["payload"]["generation"]["generation_id"]

    current_time = datetime.now(timezone.utc)

    authorisation = create_valid_authorisation()
    authorisation["issued_at"] = (current_time + timedelta(hours=1)).isoformat()
    authorisation["expires_at"] = (current_time + timedelta(hours=2)).isoformat()

    response = client.post(
        "/disclosures/resolve",
        json={
            "generation_id": generation_id,
            "authorisation": authorisation,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == ("The authorisation is not yet valid.")


def test_wrong_provider_authorisation_is_denied() -> None:
    credential = issue_test_credential()
    generation_id = credential["payload"]["generation"]["generation_id"]

    response = client.post(
        "/disclosures/resolve",
        json={
            "generation_id": generation_id,
            "authorisation": create_valid_authorisation(
                provider_id="different-provider"
            ),
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "The authorisation does not apply to this provider."
    )


def test_successful_disclosure_is_written_to_audit_log() -> None:
    credential = issue_test_credential()
    generation_id = credential["payload"]["generation"]["generation_id"]

    response = client.post(
        "/disclosures/resolve",
        json={
            "generation_id": generation_id,
            "authorisation": create_valid_authorisation(),
        },
    )

    assert response.status_code == 200

    audit_response = client.get("/disclosures/audit")

    assert audit_response.status_code == 200
    assert len(audit_response.json()) >= 1

    latest_record = audit_response.json()[-1]

    assert latest_record["generation_id"] == generation_id
    assert latest_record["authorisation_id"] == "court-order-001"
    assert latest_record["approved"] is True
    assert latest_record["denial_reason"] is None


def test_denied_disclosure_is_written_to_audit_log() -> None:
    credential = issue_test_credential()
    generation_id = credential["payload"]["generation"]["generation_id"]

    response = client.post(
        "/disclosures/resolve",
        json={
            "generation_id": generation_id,
            "authorisation": create_valid_authorisation(
                provider_id="different-provider"
            ),
        },
    )

    assert response.status_code == 403

    audit_response = client.get("/disclosures/audit")

    assert audit_response.status_code == 200
    assert len(audit_response.json()) >= 1

    latest_record = audit_response.json()[-1]

    assert latest_record["generation_id"] == generation_id
    assert latest_record["approved"] is False
    assert latest_record["denial_reason"] == (
        "The authorisation does not apply to this provider."
    )
