import base64
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.main import app  # noqa: E402


client = TestClient(app)


def issue_test_credential(
    retention_days: int = 365,
) -> dict:
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
            "retention_days": retention_days,
        },
    )

    assert response.status_code == 201

    return response.json()


def create_valid_authorisation(
    provider_id: str = "gap-demo-provider",
) -> dict:
    current_time = datetime.now(timezone.utc)

    return {
        "authorisation_id": "court-order-001",
        "investigator_reference": "investigator-001",
        "issuing_authority": "Crown Court",
        "jurisdiction": "GB",
        "purpose": "criminal-investigation",
        "issued_at": (current_time - timedelta(minutes=5)).isoformat(),
        "expires_at": (current_time + timedelta(hours=1)).isoformat(),
        "provider_id": provider_id,
    }


def test_list_providers() -> None:
    response = client.get("/providers")

    assert response.status_code == 200
    assert response.json()[0]["provider_id"] == "gap-demo-provider"


def test_provider_identity_endpoint() -> None:
    response = client.get("/providers/gap-demo-provider/.well-known/gap.json")

    assert response.status_code == 200
    assert response.json()["provider_id"] == "gap-demo-provider"


def test_issue_generation_credential() -> None:
    credential = issue_test_credential()

    assert credential["payload"]["provider"]["provider_id"] == ("gap-demo-provider")
    assert credential["proof"]["type"] == "Ed25519"


def test_invalid_retention_period_is_rejected() -> None:
    artifact = base64.b64encode(b"artifact").decode("utf-8")

    response = client.post(
        "/credentials/issue",
        json={
            "provider_id": "gap-demo-provider",
            "model_id": "demo-model-v1",
            "media_type": "text/plain",
            "artifact_base64": artifact,
            "account_reference": "user-001",
            "prompt": "Generate an artifact.",
            "retention_days": 0,
        },
    )

    assert response.status_code == 422


def test_verify_generation_credential() -> None:
    credential = issue_test_credential()

    response = client.post(
        "/credentials/verify",
        json={"credential": credential},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_tampered_credential_is_invalid() -> None:
    credential = issue_test_credential()
    credential["payload"]["model"]["model_id"] = "tampered-model"

    response = client.post(
        "/credentials/verify",
        json={"credential": credential},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False


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
    assert body["account_reference"] == "user-001"
    assert body["retention_status"] == "active"
    assert body["retained_until"] is not None


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


def test_successful_disclosure_is_audited() -> None:
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

    latest_record = audit_response.json()[-1]

    assert latest_record["generation_id"] == generation_id
    assert latest_record["approved"] is True
    assert latest_record["denial_reason"] is None


def test_denied_disclosure_is_audited() -> None:
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
    latest_record = audit_response.json()[-1]

    assert latest_record["approved"] is False
    assert latest_record["denial_reason"] == (
        "The authorisation does not apply to this provider."
    )
