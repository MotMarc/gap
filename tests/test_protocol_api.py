import base64
import sys
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

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
            "retention_days": 365,
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


def test_generate_artifact_and_issue_credential() -> None:
    response = client.post(
        "/generations/create",
        json={
            "provider_id": "gap-demo-provider",
            "account_reference": "user-001",
            "prompt": "A red geometric object on a neutral background.",
            "retention_days": 365,
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["media_type"] == "image/png"
    assert body["filename"].endswith(".png")
    assert body["credential"]["proof"]["type"] == "Ed25519"
    assert body["credential"]["payload"]["model"]["model_id"] == (
    "gap-procedural-image-v1"
)

    image_bytes = base64.b64decode(
        body["artifact_base64"],
        validate=True,
    )

    image = Image.open(BytesIO(image_bytes))

    assert image.format == "PNG"


def test_generated_artifact_credential_verifies() -> None:
    generation_response = client.post(
        "/generations/create",
        json={
            "provider_id": "gap-demo-provider",
            "account_reference": "user-001",
            "prompt": "A generated GAP verification artifact.",
            "retention_days": 365,
        },
    )

    credential = generation_response.json()["credential"]

    verification_response = client.post(
        "/credentials/verify",
        json={
            "credential": credential,
        },
    )

    assert verification_response.status_code == 200
    assert verification_response.json()["valid"] is True


def test_unknown_generation_adapter_returns_404() -> None:
    response = client.post(
        "/generations/create",
        json={
            "provider_id": "unknown-provider",
            "account_reference": "user-001",
            "prompt": "Generate an artifact.",
            "retention_days": 365,
        },
    )

    assert response.status_code == 404


def test_issue_generation_credential() -> None:
    credential = issue_test_credential()

    assert credential["payload"]["provider"]["provider_id"] == ("gap-demo-provider")
    assert credential["proof"]["type"] == "Ed25519"


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
    latest_record = audit_response.json()[-1]

    assert latest_record["generation_id"] == generation_id
    assert latest_record["approved"] is True
    assert latest_record["denial_reason"] is None
