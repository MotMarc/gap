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


def test_stylesheet_is_served() -> None:
    response = client.get("/static/styles.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert "--accent:" in response.text
    assert ".verification-timeline" in response.text
    assert ".credential-card" in response.text


def test_javascript_is_served() -> None:
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "generateArtifact" in response.text
    assert "runCompleteVerification" in response.text
    assert "calculateSha256" in response.text
    assert "tamperArtifact" in response.text
    assert "tamperCredential" in response.text
    assert "/generations/create" in response.text
    assert "/credentials/verify" in response.text


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy",
        "service": "gap-reference-implementation",
        "version": "0.7.0",
    }
