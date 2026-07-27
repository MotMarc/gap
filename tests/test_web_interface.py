import re
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


def test_frontend_reports_sprint_12_version() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Reference Demonstrator v0.12.0" in response.text
    assert "Registry Authority" in response.text
    assert "Signed trust attestation" in response.text
    assert "Transparency Log" in response.text
    assert "Potential split view detected" in response.text
    assert "Registry authority identity" in response.text
    assert "Attestation signature" in response.text
    assert "trusted-authority" in response.text


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
    assert ".registry-authority-panel" in response.text
    assert ".attestation-valid" in response.text
    assert ".transparency-log-panel" in response.text


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
    assert "/registry-authorities" in response.text
    assert "/trust-attestations" in response.text
    assert "registry_authority_id" in response.text
    assert "trusted_by_local_registry" in response.text
    assert "renderRegistryAuthorities" in response.text
    assert "renderTrustAttestations" in response.text
    assert "createRegistryAuthorityCard" in response.text
    assert "createTrustAttestationCard" in response.text
    assert "registryAuthorityGrid" in response.text
    assert "trustAttestationGrid" in response.text
    assert "trust_attestation_id" in response.text
    assert "trust_attestation_valid" in response.text
    assert "registry_authority_trusted" in response.text
    assert "authority_key_status" in response.text
    assert "timelineAuthorityIdentity" in response.text
    assert "timelineAuthorityKey" in response.text
    assert "timelineAttestation" in response.text
    assert "timelineOverall" in response.text
    assert "timelineTransparencyEntry" in response.text
    assert "timelineTransparencyProof" in response.text
    assert re.search(
        r"setTimelineState\(\s*elements\.timelineAuthorityIdentity",
        response.text,
    )
    assert re.search(
        r"setTimelineState\(\s*elements\.timelineAuthorityKey",
        response.text,
    )
    assert re.search(
        r"setTimelineState\(\s*elements\.timelineAttestation",
        response.text,
    )
    assert re.search(
        r"setTimelineState\(\s*elements\.timelineOverall",
        response.text,
    )
    assert re.search(
        r"setTimelineState\(\s*elements\.timelineTransparencyEntry",
        response.text,
    )
    assert re.search(
        r"setTimelineState\(\s*elements\.timelineTransparencyProof",
        response.text,
    )
    assert "signatureValid = verification.cryptographic_valid === true" in (
        response.text
    )
    assert "signatureValid = verification.valid" not in response.text
    assert "verification.provider_trusted === true" in response.text
    assert "verification.trust_attestation_present === true" in response.text
    assert "verification.trust_attestation_valid === true" in response.text
    assert "verification.registry_authority_trusted === true" in response.text
    assert "verification.registry_authority_key_status" in response.text
    assert "verification.transparency_verified" in response.text
    assert "verification.transparency_tree_head_id" in response.text
    assert "verification.transparency_failure_reason" in response.text
    assert "/transparency/entries" in response.text
    assert "/transparency/tree-heads" in response.text
    assert "backendOverallValid = verification.valid === true" in response.text
    assert "escapeHtml(" not in response.text
    assert ".innerHTML" not in response.text


def test_sprint_10_federation_panels_are_present() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="registry-authority-grid"' in response.text
    assert 'id="trust-attestation-grid"' in response.text
    assert "Registry Authority" in response.text
    assert "Signed trust attestation" in response.text
    for timeline_id in (
        "timeline-authority-identity",
        "timeline-authority-key",
        "timeline-attestation",
        "timeline-federation-chain",
        "timeline-federation-conflict",
        "timeline-overall",
        "timeline-transparency-entry",
        "timeline-transparency-proof",
    ):
        assert f'id="{timeline_id}"' in response.text


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "gap-reference-implementation"
    assert body["version"] == "0.12.0"
    assert body["transparency_log_loaded"] is True
    assert body["federation_invalid_file_count"] >= 0


def test_sprint_11_federation_runtime_wiring() -> None:
    html = client.get("/").text
    javascript = client.get("/static/app.js").text
    assert 'id="federation-bundle-grid"' in html
    for identifier in (
        "timelineFederationChain",
        "timelineFederationConflict",
        "federationBundleGrid",
    ):
        assert identifier in javascript
    for field in (
        "federation_conflict",
        "federation_sources",
        "federation_bundle_ids",
        "effective_provider_trust_status",
    ):
        assert field in javascript
    assert "/federation/bundles" in javascript


def test_sprint_12_inspection_dashboard_structure_and_wiring() -> None:
    page = client.get("/").text
    javascript = client.get("/static/app.js").text
    stylesheet = client.get("/static/styles.css").text

    required_ids = (
        "attestation-provider-filter",
        "attestation-status-filter",
        "attestation-history-filter",
        "attestation-search",
        "attestation-result-count",
        "toggle-tree-head-history",
        "older-checkpoint-select",
        "newer-checkpoint-select",
        "compare-checkpoints-button",
        "transparency-entry-type-filter",
        "transparency-authority-filter",
        "transparency-entry-search",
        "transparency-entry-sort",
        "transparency-entry-count",
        "transparency-entry-grid",
        "transparency-entry-explorer",
        "transparency-health-banner",
    )
    for element_id in required_ids:
        assert f'id="{element_id}"' in page
        assert element_id in javascript

    assert 'aria-expanded="false"' in page
    assert 'role="listbox"' in page
    assert 'aria-live="polite"' in page
    assert "Current only" in page
    assert "Current and history" in page
    assert "Select a log entry" in page
    assert "Loading Transparency Log" in page

    for helper in (
        "formatTechnicalValue",
        "createTechnicalValue",
        "createStatusBadge",
        "createMetadataRow",
        "createRawJsonViewer",
        "renderFilteredTrustAttestations",
        "renderTransparencyOverview",
        "renderTreeHeadHistory",
        "renderCheckpointComparison",
        "renderLogEntryList",
        "renderEntryExplorer",
    ):
        assert re.search(rf"function\s+{helper}\s*\(", javascript)

    assert "slice(0, 10)" in javascript
    assert "View decision history" in javascript
    assert "aria-selected" in javascript
    assert "navigator.clipboard.writeText" in javascript
    assert "textContent = serialized" in javascript
    assert ".innerHTML" not in javascript

    for component in (
        ".metric-grid",
        ".technical-value",
        ".data-toolbar",
        ".compact-table",
        ".entry-master-detail",
        ".entry-list-item.selected",
        ".segmented-control",
        ".raw-data-viewer",
        ".outcome-banner",
        ".loading-state",
        ".empty-state",
        ".error-state",
        ":focus-visible",
    ):
        assert component in stylesheet
    assert "@media (max-width: 1080px)" in stylesheet
    assert "@media (max-width: 768px)" in stylesheet
    assert "@media (max-width: 480px)" in stylesheet
