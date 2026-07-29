import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient


IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"
sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.main import app  # noqa: E402


client = TestClient(app)


def source(path: str) -> str:
    return client.get(path).text.replace("\r\n", "\n")


def test_browser_application_and_assets_are_served() -> None:
    page = client.get("/")
    css = client.get("/static/styles.css")
    script = client.get("/static/app.js")
    assert page.status_code == css.status_code == script.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert css.headers["content-type"].startswith("text/css")
    assert "Generation Attribution Protocol" in page.text
    assert "Verifiable provenance for AI-generated media" in page.text


def test_exactly_four_primary_navigation_destinations() -> None:
    page = source("/")
    links = re.findall(r"<a[^>]*data-primary-nav[^>]*>([^<]+)</a>", page)
    assert links == ["Home", "Create", "Explore", "Developer"]
    assert 'data-route="verify"' not in page
    assert 'data-route="credential"' not in page
    assert ">Inspect Credential<" not in page


def test_home_is_default_and_compact() -> None:
    page = source("/")
    script = source("/static/app.js")
    assert 'data-page="home"' in page
    assert 'data-page="create" hidden' in page
    assert 'data-page="explore" hidden' in page
    assert 'data-page="developer" hidden' in page
    assert 'window.location.hash.slice(1).split("/")[0] || "home"' in script
    assert "Create and verify an artifact" in page
    assert "Verify an existing credential" in page
    for word in ("Create", "Publish", "Verify"):
        assert f"<h2>{word}</h2>" in page
    assert "Reference system healthy" in page
    assert "View infrastructure status" in page


def test_old_guided_interface_is_deleted() -> None:
    combined = "\n".join(
        (source("/"), source("/static/app.js"), source("/static/styles.css"))
    )
    for obsolete in (
        "Guided Demo",
        "guided-demo",
        "guided-stepper",
        "Step 8 of 8",
        "workflow-circle",
        "moveGuidedDemo",
        "renderGuidedDemoStep",
        "restartGuidedDemo",
        "overview-trust-chain",
        "Generate, credential and verify",
        "View verification result",
    ):
        assert obsolete not in combined
    assert combined.count(">Restart<") == 0


def test_create_is_one_state_driven_workflow() -> None:
    page = source("/")
    script = source("/static/app.js")
    assert page.count('id="create-workflow"') == 1
    for workflow_state in (
        '"idle"',
        '"generating"',
        '"generated"',
        '"verifying"',
        '"verified"',
        '"failed"',
        '"tampering"',
    ):
        assert workflow_state in script
    assert page.count('data-workflow-state="idle"') == 1
    assert "state.workflow" in script
    assert "wizard" not in script.lower()
    assert "stepper" not in script.lower()


def test_initial_create_state_is_minimal() -> None:
    page = source("/")
    idle = page.split('<template id="create-idle-template">', 1)[1].split(
        "</template>", 1
    )[0]
    assert 'id="provider-id"' in idle
    assert 'id="generation-prompt"' in idle
    assert "Generate artifact" in idle
    assert "A GAP credential will be issued automatically" in idle
    assert "Verify provenance" not in idle
    assert "technical" not in idle.lower()


def test_generated_state_exposes_one_primary_verification_action() -> None:
    page = source("/")
    generated = page.split('<template id="create-generated-template">', 1)[1].split(
        "</template>", 1
    )[0]
    assert "Artifact preview" in generated
    assert "Verify provenance" in generated
    assert "Generate another" in generated
    assert "<summary>Issued credential</summary>" in generated
    assert generated.count("primary-button") == 1


def test_verification_has_five_high_level_automatic_checks() -> None:
    page = source("/")
    progress = page.split('<template id="create-verifying-template">', 1)[1].split(
        "</template>", 1
    )[0]
    checks = re.findall(r'data-check="([^"]+)"', progress)
    assert checks == [
        "integrity",
        "authenticity",
        "trust",
        "transparency",
        "witnesses",
    ]
    assert "Verifying provenance" in progress
    assert "timeline-" not in progress


def test_verified_result_precedes_collapsed_evidence() -> None:
    page = source("/")
    verified = page.split('<template id="create-verified-template">', 1)[1].split(
        "</template>", 1
    )[0]
    assert verified.index("<h2>Verified</h2>") < verified.index(
        "Technical verification evidence"
    )
    assert "<details" in verified
    assert "<details open" not in verified
    for result in (
        "Artifact integrity",
        "Provider signature",
        "Provider trust",
        "Transparency evidence",
        "Witness quorum",
    ):
        assert result in verified
    assert "View artifact" in verified
    assert "Test tampering detection" in verified
    assert "Start again" in verified


def test_tampering_is_only_revealed_after_success() -> None:
    page = source("/")
    script = source("/static/app.js")
    initial = page.split('<template id="create-idle-template">', 1)[1].split(
        "</template>", 1
    )[0]
    assert "Modify artifact" not in initial
    for label in (
        "Modify artifact",
        "Modify credential",
        "Substitute provider",
        "Reference revoked key",
    ):
        assert label in script
    assert "runTamperingScenario" in script
    assert "Restore original artifact" in page


def test_explore_has_four_categories_and_nested_gossip() -> None:
    page = source("/")
    categories = re.findall(r'data-explore-tab="([^"]+)"', page)
    assert categories == ["providers", "authorities", "transparency", "witnesses"]
    assert 'data-explore-tab="gossip"' not in page
    script = source("/static/app.js")
    assert "Checkpoint monitoring" in script
    assert "No conflicting checkpoint views detected" in script


def test_explore_lists_are_bounded_and_master_detail() -> None:
    script = source("/static/app.js")
    stylesheet = source("/static/styles.css")
    assert "providers.slice(0, 6)" in script
    assert "authorities.slice(0, 6)" in script
    assert script.count(".slice(0, 10)") >= 8
    assert "master-detail" in script
    assert ".master-detail" in stylesheet
    for section in (
        "Key history",
        "Trust-decision history",
        "Signed attestation",
        "Identity document",
        "Raw JSON",
    ):
        assert section in script


def test_transparency_details_are_mutually_exclusive() -> None:
    script = source("/static/app.js")
    for label in ("Browse entries", "View checkpoints", "Inspect proof"):
        assert label in script
    assert 'container.querySelector(".detail-view")?.remove()' in script
    assert "Transparency log healthy" in script
    assert "Append-only consistency" in script


def test_developer_owns_raw_technical_data() -> None:
    page = source("/")
    script = source("/static/app.js")
    tabs = re.findall(r'data-developer-tab="([^"]+)"', page)
    assert tabs == ["integration", "api", "protocol", "raw"]
    assert 'developerTab: "integration"' in script
    for object_type in (
        "credentials",
        "provider identities",
        "attestations",
        "federation bundles",
        "tree heads",
        "proofs",
        "witness statements",
        "gossip evidence",
    ):
        assert object_type in script
    assert 'element("details", {className: "disclosure"})' in script
    assert "viewer.open = false" in script


def test_raw_json_is_not_visible_by_default() -> None:
    page = source("/")
    assert "<details open" not in page
    home = page.split('id="page-home"', 1)[1].split("</section>", 1)[0]
    assert "<pre" not in home
    idle = page.split('<template id="create-idle-template">', 1)[1].split(
        "</template>", 1
    )[0]
    assert "<pre" not in idle


def test_sprint_13_verification_fields_are_independently_processed() -> None:
    script = source("/static/app.js")
    required_fields = (
        "cryptographic_valid",
        "provider_trusted",
        "trust_attestation_present",
        "trust_attestation_valid",
        "registry_authority_trusted",
        "registry_authority_key_status",
        "effective_provider_trust_status",
        "federation_conflict",
        "federation_sources",
        "federation_bundle_ids",
        "transparency_verified",
        "transparency_tree_head_id",
        "transparency_consistency_valid",
        "witness_quorum_met",
        "checkpoint_gossip_consistent",
        "split_view_detected",
        "witness_equivocation_detected",
    )
    for field in required_fields:
        assert field in script
    assert "signatureValid = verification.cryptographic_valid === true" in script
    assert "signatureValid = verification.valid" not in script
    assert "witnessQuorumMet = verification.witness_quorum_met === true" in script
    assert "splitViewDetected = verification.split_view_detected === true" in script
    assert "backendOverallValid = verification.valid === true" in script
    assert len(re.findall(r"verification\.valid\s*===", script)) == 1


def test_live_api_routes_remain_wired() -> None:
    script = source("/static/app.js")
    for route in (
        "/generations/create",
        "/credentials/verify",
        "/providers",
        "/trust-registry",
        "/registry-authorities",
        "/trust-attestations",
        "/federation/bundles",
        "/transparency/entries",
        "/transparency/tree-heads",
        "/transparency/witnesses",
        "/transparency/witness-statements",
        "/transparency/witness-quorum",
        "/transparency/gossip/status",
        "/transparency/gossip/observations",
    ):
        assert route in script


def test_all_required_dom_elements_and_helpers_resolve() -> None:
    page = source("/")
    script = source("/static/app.js")
    ids = set(re.findall(r'\bid="([^"]+)"', page))
    queried_ids = set(re.findall(r'querySelector\("#([^"]+)"\)', script))
    assert queried_ids <= ids
    helpers = set(re.findall(r"^function\s+([A-Za-z]\w*)\s*\(", script, re.M))
    async_helpers = set(
        re.findall(r"^async function\s+([A-Za-z]\w*)\s*\(", script, re.M)
    )
    defined = helpers | async_helpers
    for helper in (
        "generateArtifact",
        "runCompleteVerification",
        "calculateSha256",
        "formatTechnicalValue",
        "createTechnicalValue",
        "createStatusLine",
        "createDisclosure",
        "createLoadingState",
        "createEmptyState",
        "createErrorState",
        "normalizeWitnessListResponse",
        "normalizeWitnessStatementListResponse",
        "normalizeGossipStatusResponse",
        "normalizeGossipObservationListResponse",
        "normalizeGossipObservation",
    ):
        assert helper in defined
    assert ".innerHTML" not in script
    assert "escapeHtml(" not in script


def test_simplified_css_system_and_no_nested_card_rules() -> None:
    stylesheet = source("/static/styles.css")
    for variable in (
        "--page-background:",
        "--surface:",
        "--border:",
        "--text:",
        "--muted:",
        "--accent:",
        "--success:",
        "--warning:",
        "--danger:",
        "--space:",
        "--content-width: 1120px",
    ):
        assert variable in stylesheet
    assert "--reading-width: 720px" in stylesheet
    assert stylesheet.count("border-radius: var(--radius)") >= 8
    for obsolete in (
        ".credential-card",
        ".guided-stepper",
        ".workflow-circle",
        ".overview-trust-chain",
        ".hero-diagram",
        ".card .card",
    ):
        assert obsolete not in stylesheet
    assert "@media (max-width: 820px)" in stylesheet
    assert "@media (max-width: 520px)" in stylesheet
    assert "prefers-reduced-motion" in stylesheet


def test_mobile_navigation_is_accessible() -> None:
    page = source("/")
    script = source("/static/app.js")
    assert 'id="mobile-menu-toggle"' in page
    assert 'aria-controls="primary-navigation"' in page
    assert 'aria-expanded="false"' in page
    assert 'setAttribute("aria-expanded", String(open))' in script


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "gap-reference-implementation"
    assert body["version"] == "0.16.0"
    assert body["transparency_log_loaded"] is True
    assert body["federation_invalid_file_count"] >= 0
