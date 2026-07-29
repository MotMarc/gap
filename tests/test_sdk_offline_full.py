import hashlib
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.provider_config import DEMO_PROVIDER
from app.main import app
from app.services.provider_identity_service import create_provider_identity_document
from gap_sdk import GapProvider, GapServiceClient, GapVerifier, VerificationLevel
from gap_sdk.cache import TrustMaterialCache
from gap_sdk.errors import TrustMaterialError
from gap_sdk.serialization import canonical_json
from gap_sdk.trust import load_trust_material, save_trust_material


def bundle(state):
    return {
        "manifest": {"sha256": hashlib.sha256(canonical_json(state)).hexdigest()},
        "state": state,
    }


@pytest.fixture
def full_evidence():
    client = TestClient(app)
    state = client.get("/public-state").json()
    identity = create_provider_identity_document(DEMO_PROVIDER)
    provider = GapProvider.from_key_file(
        identity, DEMO_PROVIDER.active_signing_key.private_key_path
    )
    artifact = b"Sprint 15 repository-free full verification\n"
    credential = provider.issue_credential(
        artifact, {"model": "offline-full-equivalence"}
    )
    return client, state, artifact, credential


def test_online_and_offline_full_policy_are_equivalent(full_evidence):
    client, state, artifact, credential = full_evidence
    online = client.post(
        "/credentials/verify",
        json={"credential": credential.model_dump(mode="json")},
    ).json()
    offline = GapVerifier.from_trust_material(bundle(state)).verify(
        artifact, credential
    )
    assert offline.valid == online["valid"]
    assert offline.achieved_level == VerificationLevel.FULL
    for field in (
        "cryptographic_valid",
        "provider_trusted",
        "transparency_verified",
        "witness_quorum_met",
        "checkpoint_gossip_consistent",
        "federation_conflict",
        "split_view_detected",
        "witness_equivocation_detected",
    ):
        assert getattr(offline, field) == online[field]
    assert [check.code for check in offline.checks] == [
        "artifact-digest",
        "provider-signature",
        "provider-trusted",
        "transparency-verified",
        "witness-quorum-met",
        "checkpoint-gossip-consistent",
    ]


def test_offline_full_tampering_and_missing_evidence_fail_closed(full_evidence):
    _, state, artifact, credential = full_evidence
    verifier = GapVerifier.from_trust_material(bundle(state))
    assert not verifier.verify(artifact + b"tampered", credential).valid
    missing = json.loads(json.dumps(state))
    missing["witness_identities"] = []
    result = GapVerifier.from_trust_material(bundle(missing)).verify(
        artifact, credential
    )
    assert not result.valid
    assert result.achieved_level != VerificationLevel.FULL


def test_stale_material_cannot_achieve_full(full_evidence):
    _, state, artifact, credential = full_evidence
    state["exported_at"] = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    result = GapVerifier.from_trust_material(
        bundle(state), maximum_age_seconds=3600
    ).verify(artifact, credential)
    assert not result.valid
    assert result.failure_code == "stale-trust-material"
    assert result.achieved_level == VerificationLevel.CRYPTOGRAPHIC


def test_public_export_client_and_cache(full_evidence, tmp_path):
    _, state, _, _ = full_evidence
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=state))
    client = GapServiceClient("https://gap.example", transport=transport)
    output = tmp_path / "trust.json"
    client.export_trust_material(output)
    assert load_trust_material(output).state["private_data_included"] is False
    cache = TrustMaterialCache(tmp_path / "cache")
    assert cache.refresh(client).state["bundle_format"] == "gap-public-state-v2"
    cache.path.write_text("{}", encoding="utf-8")
    with pytest.raises(TrustMaterialError):
        cache.load()


def test_failed_cache_refresh_preserves_valid_cache(full_evidence, tmp_path):
    _, state, _, _ = full_evidence
    cache = TrustMaterialCache(tmp_path)
    save_trust_material(state, cache.path)
    original = cache.path.read_bytes()

    class FailedClient:
        def export_trust_material(self):
            raise RuntimeError("refresh failed")

    with pytest.raises(RuntimeError):
        cache.refresh(FailedClient())
    assert cache.path.read_bytes() == original
