import base64
import sys
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
        },
    )

    assert response.status_code == 201

    return response.json()


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
        },
    )

    assert response.status_code == 422
