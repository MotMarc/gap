import base64
import sys
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.core.provider_config import provider_repository  # noqa: E402
from app.crypto.provider_keys import load_private_key  # noqa: E402
from app.main import app  # noqa: E402
from app.services.artifact_service import create_artifact_descriptor  # noqa: E402
from app.services.generation_credential_service import (  # noqa: E402
    create_credential_payload,
    issue_generation_credential,
)
from app.services.generation_event_service import create_generation_event  # noqa: E402


client = TestClient(app)


ACTIVE_KEY_IDS = {
    "gap-demo-provider": "demo-key-2026-02",
    "aurora-ai": "aurora-key-2026-02",
    "meridian-ai": "meridian-key-2026-02",
}


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


def create_credential_with_provider_key(
    provider_id: str,
    key_id: str,
) -> dict:
    provider = provider_repository.get(provider_id)
    signing_key = provider.get_signing_key(key_id)

    assert signing_key.private_key_path is not None

    event = create_generation_event(
        provider_id=provider_id,
        model_id="historical-model-v1",
    )
    descriptor = create_artifact_descriptor(
        artifact=b"historical GAP artifact",
        media_type="text/plain",
    )
    payload = create_credential_payload(
        event=event,
        artifacts=[descriptor],
    )

    credential = issue_generation_credential(
        payload=payload,
        key_id=key_id,
        private_key=load_private_key(signing_key.private_key_path),
    )

    return credential.model_dump(mode="json")


def test_list_providers() -> None:
    response = client.get("/providers")

    assert response.status_code == 200

    providers = {provider["provider_id"]: provider for provider in response.json()}

    assert set(providers) == {
        "gap-demo-provider",
        "aurora-ai",
        "meridian-ai",
    }

    for provider_id, active_key_id in ACTIVE_KEY_IDS.items():
        assert providers[provider_id]["active_key_id"] == active_key_id
        assert providers[provider_id]["published_key_count"] >= 2


def test_provider_identity_endpoint() -> None:
    response = client.get("/providers/gap-demo-provider/.well-known/gap.json")

    assert response.status_code == 200

    document = response.json()

    assert document["provider_id"] == "gap-demo-provider"
    assert document["active_key_id"] == "demo-key-2026-02"


def test_every_provider_exposes_key_history() -> None:
    all_public_keys = set()

    for provider_id, active_key_id in ACTIVE_KEY_IDS.items():
        response = client.get(
            f"/providers/{provider_id}/.well-known/gap.json",
        )

        assert response.status_code == 200

        document = response.json()
        keys = document["keys"]
        statuses = [key["status"] for key in keys]

        assert document["provider_id"] == provider_id
        assert document["active_key_id"] == active_key_id
        assert statuses.count("active") == 1
        assert "retired" in statuses

        for key in keys:
            assert key["algorithm"] == "Ed25519"
            assert key["created_at"]
            all_public_keys.add(key["public_key"])

    assert len(all_public_keys) == 7


def test_demo_provider_publishes_revoked_key_metadata() -> None:
    response = client.get("/providers/gap-demo-provider/.well-known/gap.json")
    document = response.json()

    revoked_key = next(key for key in document["keys"] if key["status"] == "revoked")

    assert revoked_key["key_id"] == "demo-key-2025-compromised"
    assert revoked_key["revoked_at"] is not None
    assert revoked_key["revocation_reason"] == "Demonstration key compromise"


def test_aurora_generates_with_active_key() -> None:
    response = client.post(
        "/generations/create",
        json={
            "provider_id": "aurora-ai",
            "account_reference": "aurora-user-001",
            "prompt": "A luminous abstract research landscape.",
            "retention_days": 365,
        },
    )

    assert response.status_code == 201

    body = response.json()
    credential = body["credential"]

    assert body["media_type"] == "image/svg+xml"
    assert body["filename"].endswith(".svg")
    assert credential["payload"]["provider"]["provider_id"] == "aurora-ai"
    assert credential["payload"]["model"]["model_id"] == "aurora-spectrum-v1"
    assert credential["proof"]["key_id"] == "aurora-key-2026-02"

    verification = client.post(
        "/credentials/verify",
        json={"credential": credential},
    )

    assert verification.status_code == 200
    assert verification.json()["valid"] is True
    assert verification.json()["key_status"] == "active"
    assert verification.json()["failure_reason"] is None


def test_meridian_generates_with_active_key() -> None:
    response = client.post(
        "/generations/create",
        json={
            "provider_id": "meridian-ai",
            "account_reference": "meridian-user-001",
            "prompt": "A structured geometric research composition.",
            "retention_days": 365,
        },
    )

    assert response.status_code == 201

    body = response.json()
    credential = body["credential"]

    assert body["media_type"] == "image/svg+xml"
    assert body["filename"].endswith(".svg")
    assert credential["payload"]["provider"]["provider_id"] == "meridian-ai"
    assert credential["payload"]["model"]["model_id"] == ("meridian-geometry-v1")
    assert credential["proof"]["key_id"] == "meridian-key-2026-02"

    verification = client.post(
        "/credentials/verify",
        json={"credential": credential},
    )

    assert verification.status_code == 200
    assert verification.json()["valid"] is True
    assert verification.json()["key_status"] == "active"


def test_retired_key_credential_remains_valid() -> None:
    credential = create_credential_with_provider_key(
        provider_id="gap-demo-provider",
        key_id="demo-key-2026-01",
    )

    response = client.post(
        "/credentials/verify",
        json={"credential": credential},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["key_status"] == "retired"
    assert response.json()["failure_reason"] is None


def test_revoked_key_identifier_is_rejected() -> None:
    credential = issue_test_credential()
    credential["proof"]["key_id"] = "demo-key-2025-compromised"

    response = client.post(
        "/credentials/verify",
        json={"credential": credential},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["key_status"] == "revoked"
    assert response.json()["failure_reason"] == "revoked-key"


def test_provider_substitution_invalidates_credential() -> None:
    generation_response = client.post(
        "/generations/create",
        json={
            "provider_id": "aurora-ai",
            "account_reference": "user-001",
            "prompt": "A provider substitution test.",
            "retention_days": 365,
        },
    )

    assert generation_response.status_code == 201

    credential = generation_response.json()["credential"]
    credential["payload"]["provider"]["provider_id"] = "meridian-ai"

    verification_response = client.post(
        "/credentials/verify",
        json={"credential": credential},
    )

    assert verification_response.status_code == 200
    assert verification_response.json()["valid"] is False
    assert verification_response.json()["failure_reason"] == "unknown-key"


def test_key_identifier_substitution_invalidates_credential() -> None:
    generation_response = client.post(
        "/generations/create",
        json={
            "provider_id": "aurora-ai",
            "account_reference": "user-001",
            "prompt": "A signing key substitution test.",
            "retention_days": 365,
        },
    )

    assert generation_response.status_code == 201

    credential = generation_response.json()["credential"]
    credential["proof"]["key_id"] = "aurora-key-2026-01"

    verification_response = client.post(
        "/credentials/verify",
        json={"credential": credential},
    )

    assert verification_response.status_code == 200
    assert verification_response.json()["valid"] is False
    assert verification_response.json()["key_status"] == "retired"
    assert verification_response.json()["failure_reason"] == "invalid-signature"


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
    assert body["credential"]["proof"]["key_id"] == "demo-key-2026-02"
    assert body["credential"]["payload"]["model"]["model_id"] == (
        "gap-semantic-procedural-image-v2"
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
        json={"credential": credential},
    )

    assert verification_response.status_code == 200
    assert verification_response.json()["valid"] is True
    assert verification_response.json()["key_status"] == "active"


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
    assert credential["proof"]["key_id"] == "demo-key-2026-02"


def test_verify_generation_credential() -> None:
    credential = issue_test_credential()

    response = client.post(
        "/credentials/verify",
        json={"credential": credential},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["failure_reason"] is None


def test_tampered_credential_is_invalid() -> None:
    credential = issue_test_credential()
    credential["payload"]["model"]["model_id"] = "tampered-model"

    response = client.post(
        "/credentials/verify",
        json={"credential": credential},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["failure_reason"] == "invalid-signature"


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
