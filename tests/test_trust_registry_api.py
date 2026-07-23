import base64
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.core.repositories import trust_registry_service  # noqa: E402
from app.main import app  # noqa: E402


client = TestClient(app)


def issue_demo_credential() -> dict:
    response = client.post(
        "/credentials/issue",
        json={
            "provider_id": "gap-demo-provider",
            "model_id": "demo-model-v1",
            "media_type": "text/plain",
            "artifact_base64": base64.b64encode(
                b"Sprint 9 trust verification artifact"
            ).decode("utf-8"),
            "account_reference": "user-001",
            "prompt": "Create a Sprint 9 trust verification artifact.",
            "retention_days": 365,
        },
    )

    assert response.status_code == 201
    return response.json()


def test_provider_listing_includes_independent_trust_state() -> None:
    response = client.get("/providers")

    assert response.status_code == 200

    providers = response.json()

    assert len(providers) == 3

    for provider in providers:
        assert provider["trust_status"] == "approved"
        assert provider["provider_trusted"] is True


def test_trust_registry_lists_seeded_approved_providers() -> None:
    response = client.get("/trust-registry")

    assert response.status_code == 200

    entries = {entry["provider_id"]: entry for entry in response.json()}

    assert set(entries) >= {
        "gap-demo-provider",
        "aurora-ai",
        "meridian-ai",
    }

    for provider_id in (
        "gap-demo-provider",
        "aurora-ai",
        "meridian-ai",
    ):
        assert entries[provider_id]["status"] == "approved"
        assert entries[provider_id]["trusted"] is True
        assert entries[provider_id]["latest_decision_id"]


def test_provider_trust_endpoint_returns_decision_history() -> None:
    response = client.get("/providers/gap-demo-provider/trust")

    assert response.status_code == 200

    body = response.json()

    assert body["provider_id"] == "gap-demo-provider"
    assert body["status"] == "approved"
    assert body["trusted"] is True
    assert body["latest_decision"]["status"] == "approved"
    assert [decision["status"] for decision in body["decision_history"]] == [
        "applicant",
        "approved",
    ]


def test_unknown_provider_trust_endpoint_returns_404() -> None:
    response = client.get("/providers/not-registered/trust")

    assert response.status_code == 404


def test_application_submission_is_publicly_redacted() -> None:
    response = client.post(
        "/provider-applications",
        json={
            "provider_id": "sprint9-applicant-one",
            "provider_name": "Sprint 9 Applicant One",
            "contact_reference": "private-contact@example.test",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["provider_id"] == "sprint9-applicant-one"
    assert body["application_status"] == "submitted"
    assert body["trust_status"] == "applicant"
    assert "contact_reference" not in body

    registry_response = client.get("/trust-registry")
    registry_text = registry_response.text

    assert "private-contact@example.test" not in registry_text


def test_duplicate_active_application_returns_conflict() -> None:
    payload = {
        "provider_id": "sprint9-applicant-two",
        "provider_name": "Sprint 9 Applicant Two",
        "contact_reference": "private-contact-two@example.test",
    }

    first_response = client.post(
        "/provider-applications",
        json=payload,
    )
    second_response = client.post(
        "/provider-applications",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


@pytest.mark.parametrize(
    "trust_status",
    [
        "self-declared",
        "applicant",
        "suspended",
        "removed",
    ],
)
def test_untrusted_provider_cannot_issue_credentials(
    monkeypatch: pytest.MonkeyPatch,
    trust_status: str,
) -> None:
    monkeypatch.setattr(
        trust_registry_service,
        "get_current_status",
        lambda provider_id: trust_status,
    )

    response = client.post(
        "/credentials/issue",
        json={
            "provider_id": "gap-demo-provider",
            "model_id": "demo-model-v1",
            "media_type": "text/plain",
            "artifact_base64": base64.b64encode(b"Blocked issuance artifact").decode(
                "utf-8"
            ),
            "account_reference": "user-001",
            "prompt": "This issuance should be blocked.",
            "retention_days": 365,
        },
    )

    assert response.status_code == 403
    assert trust_status in response.json()["detail"]


def test_approved_provider_verification_is_fully_valid() -> None:
    credential = issue_demo_credential()

    response = client.post(
        "/credentials/verify",
        json={"credential": credential},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["cryptographic_valid"] is True
    assert body["provider_trusted"] is True
    assert body["provider_trust_status"] == "approved"
    assert body["valid"] is True
    assert body["trust_decision_id"]
    assert body["failure_reason"] is None


@pytest.mark.parametrize(
    "trust_status",
    [
        "suspended",
        "removed",
    ],
)
def test_authentic_untrusted_credential_fails_overall_verification(
    monkeypatch: pytest.MonkeyPatch,
    trust_status: str,
) -> None:
    credential = issue_demo_credential()

    monkeypatch.setattr(
        trust_registry_service,
        "get_current_status",
        lambda provider_id: trust_status,
    )
    monkeypatch.setattr(
        trust_registry_service,
        "get_current_decision",
        lambda provider_id: None,
    )

    response = client.post(
        "/credentials/verify",
        json={"credential": credential},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["cryptographic_valid"] is True
    assert body["provider_trusted"] is False
    assert body["provider_trust_status"] == trust_status
    assert body["valid"] is False
    assert body["failure_reason"] == "provider-untrusted"


def test_cryptographic_failure_remains_distinct_from_trust() -> None:
    credential = issue_demo_credential()
    credential["payload"]["model"]["model_id"] = "tampered-model"

    response = client.post(
        "/credentials/verify",
        json={"credential": credential},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["cryptographic_valid"] is False
    assert body["provider_trusted"] is True
    assert body["valid"] is False
    assert body["failure_reason"] == "invalid-signature"


def test_identity_document_cannot_self_assert_registry_trust() -> None:
    response = client.get("/providers/gap-demo-provider/.well-known/gap.json")

    assert response.status_code == 200

    document = response.json()

    assert "trust_status" not in document
    assert "provider_trusted" not in document
    assert "trusted" not in document
