import base64
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.core.repositories import trust_registry_service  # noqa: E402
from app.main import app  # noqa: E402
from app.services.trust_registry_service import ProviderTrustEvaluation  # noqa: E402


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


def test_registry_authority_and_attestation_endpoints() -> None:
    authorities = client.get("/registry-authorities")
    assert authorities.status_code == 200
    authority = authorities.json()[0]
    assert authority["authority_id"] == "gap-reference-registry"
    assert authority["trusted_by_local_registry"] is True

    identity = client.get(
        "/registry-authorities/gap-reference-registry/.well-known/gap-registry.json"
    )
    assert identity.status_code == 200
    assert identity.json()["keys"][0]["algorithm"] == "Ed25519"
    assert "private_key" not in identity.text

    assert (
        client.get(
            "/registry-authorities/unknown/.well-known/gap-registry.json"
        ).status_code
        == 404
    )

    attestations = client.get(
        "/trust-attestations", params={"provider_id": "gap-demo-provider"}
    )
    assert attestations.status_code == 200
    assert len(attestations.json()) == 2
    attestation_id = attestations.json()[-1]["payload"]["attestation_id"]
    assert client.get(f"/trust-attestations/{attestation_id}").status_code == 200


def test_verification_exposes_signed_registry_trust() -> None:
    response = client.post(
        "/credentials/verify", json={"credential": issue_demo_credential()}
    )
    body = response.json()
    assert body["trust_attestation_present"] is True
    assert body["trust_attestation_valid"] is True
    assert body["registry_authority_id"] == "gap-reference-registry"
    assert body["registry_authority_trusted"] is True
    assert body["registry_authority_key_id"] == "gap-registry-key-2026-01"
    assert body["registry_authority_key_status"] == "active"
    assert body["trust_failure_reason"] is None
    expected_fields = {
        "valid",
        "cryptographic_valid",
        "provider_trusted",
        "provider_trust_status",
        "trust_decision_id",
        "trust_attestation_present",
        "trust_attestation_valid",
        "trust_attestation_id",
        "registry_authority_id",
        "registry_authority_trusted",
        "registry_authority_key_id",
        "registry_authority_key_status",
        "trust_failure_reason",
        "failure_reason",
    }
    assert expected_fields <= body.keys()


@pytest.mark.parametrize(
    (
        "attestation_present",
        "attestation_valid",
        "authority_id",
        "authority_trusted",
        "key_status",
        "failure_reason",
    ),
    [
        (False, False, None, False, None, "missing-trust-attestation"),
        (
            True,
            False,
            "unknown-authority",
            False,
            None,
            "unknown-registry-authority",
        ),
        (
            True,
            False,
            "gap-reference-registry",
            True,
            "revoked",
            "revoked-authority-key",
        ),
        (
            True,
            False,
            "gap-reference-registry",
            True,
            "active",
            "invalid-attestation-signature",
        ),
    ],
)
def test_verification_exposes_registry_trust_failures(
    monkeypatch: pytest.MonkeyPatch,
    attestation_present: bool,
    attestation_valid: bool,
    authority_id: str | None,
    authority_trusted: bool,
    key_status: str | None,
    failure_reason: str,
) -> None:
    credential = issue_demo_credential()
    monkeypatch.setattr(
        trust_registry_service,
        "evaluate_provider_trust",
        lambda provider_id: ProviderTrustEvaluation(
            provider_status="approved",
            provider_approved=True,
            attestation_present=attestation_present,
            attestation_valid=attestation_valid,
            registry_authority_id=authority_id,
            registry_authority_trusted=authority_trusted,
            authority_key_id=("test-authority-key" if attestation_present else None),
            authority_key_status=key_status,
            trust_decision_id="test-decision",
            trust_attestation_id=("test-attestation" if attestation_present else None),
            trust_failure_reason=failure_reason,
            trusted=False,
        ),
    )

    response = client.post("/credentials/verify", json={"credential": credential})
    body = response.json()

    assert response.status_code == 200
    assert body["cryptographic_valid"] is True
    assert body["provider_trusted"] is False
    assert body["trust_attestation_present"] is attestation_present
    assert body["trust_attestation_valid"] is attestation_valid
    assert body["registry_authority_id"] == authority_id
    assert body["registry_authority_trusted"] is authority_trusted
    assert body["registry_authority_key_status"] == key_status
    assert body["trust_failure_reason"] == failure_reason
    assert body["valid"] is False
