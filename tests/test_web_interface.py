import sys
from pathlib import Path

from fastapi.testclient import TestClient


IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.main import app  # noqa: E402


client = TestClient(app)


def test_browser_demonstrator_is_served() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Generation Attribution Protocol" in response.text
    assert "Generate and issue credential" in response.text


def test_verification_interface_is_present() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Verify an artifact against its credential" in response.text
    assert "Run complete verification" in response.text
    assert "Modify artifact bytes" in response.text
    assert "Modify credential model ID" in response.text
    assert "Reference revoked key" in response.text
    assert "Independent registry trust" in response.text
    assert "GAP Trust Registry" in response.text


def test_credential_explorer_is_present() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Credential Explorer" in response.text
    assert "Artifact descriptor" in response.text
    assert "Digital signature" in response.text


def test_protocol_explanation_is_present() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "How GAP works" in response.text
    assert "Controlled disclosure" in response.text
    assert "Signing-key lifecycle" in response.text
    assert "independent registry trust" in response.text


def test_trust_registry_interface_is_present() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Trust Registry" in response.text
    assert "Cryptographic identity does not equal ecosystem trust" in response.text
    assert 'id="trust-registry-grid"' in response.text
    assert "Provider lifecycle" in response.text
    assert "Self-declared" in response.text
    assert "Applicant" in response.text
    assert "Approved" in response.text
    assert "Suspended" in response.text
    assert "Removed" in response.text


def test_frontend_reports_sprint_9_version() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Reference Demonstrator v0.9.0" in response.text


def test_stylesheet_is_served() -> None:
    response = client.get("/static/styles.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert "--accent:" in response.text
    assert ".verification-timeline" in response.text
    assert ".credential-card" in response.text
    assert ".provider-key-history" in response.text
    assert ".trust-registry-grid" in response.text
    assert ".trust-status-approved" in response.text
    assert ".verification-result-warning" in response.text


def test_javascript_is_served() -> None:
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "generateArtifact" in response.text
    assert "runCompleteVerification" in response.text
    assert "calculateSha256" in response.text
    assert "tamperArtifact" in response.text
    assert "tamperCredential" in response.text
    assert "tamperRevokedKey" in response.text
    assert "renderProviderKeyHistory" in response.text
    assert "renderTrustRegistry" in response.text
    assert "readProviderTrust" in response.text
    assert "cryptographic_valid" in response.text
    assert "provider_trusted" in response.text
    assert "/generations/create" in response.text
    assert "/credentials/verify" in response.text
    assert "/trust-registry" in response.text


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy",
        "service": "gap-reference-implementation",
        "version": "0.9.0",
    }
