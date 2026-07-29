import base64
import hashlib
import json
from datetime import datetime, timezone

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    NoEncryption,
)

from app.crypto.provider_keys import encode_public_key
from app.services.verification_service import verify_generation_credential
from gap_sdk import (
    GapAdministrativeClient,
    GapProvider,
    GapServiceClient,
    GapVerifier,
    VerificationLevel,
)
from gap_sdk.errors import CredentialError, KeyError, ServiceError, TrustMaterialError
from gap_sdk.files import credential_path_for_artifact, read_sidecar, sha256_file
from gap_sdk.models import ProviderIdentity
from gap_sdk.serialization import canonical_json
from gap_sdk.trust import load_trust_material, save_trust_material


@pytest.fixture
def provider(tmp_path):
    private = Ed25519PrivateKey.generate()
    key_path = tmp_path / "TEST_ONLY_private.key"
    raw = private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    key_path.write_text(base64.b64encode(raw).decode(), encoding="utf-8")
    identity = ProviderIdentity(
        provider_id="test-only-provider",
        provider_name="TEST ONLY Provider",
        active_key_id="test-only-key",
        keys=[
            {
                "key_id": "test-only-key",
                "public_key": encode_public_key(private.public_key()),
                "status": "active",
                "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            }
        ],
    )
    return GapProvider.from_key_file(identity, key_path)


def test_provider_issue_is_backend_compatible(provider):
    artifact = b"test-only artifact"
    credential = provider.issue_credential(
        artifact,
        {
            "model": "test-model",
            "request_id": "test-generation",
            "created_at": "2026-01-01T00:00:00Z",
            "media_type": "text/plain",
        },
    )
    assert (
        credential.payload.artifacts[0].digest.value
        == hashlib.sha256(artifact).hexdigest()
    )
    assert verify_generation_credential(credential, provider.identity)
    assert "private" not in credential.model_dump_json()


def test_provider_file_sidecar_round_trip_and_overwrite(provider, tmp_path):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"a" * (1024 * 1024 + 3))
    credential = provider.issue_credential_for_file(artifact, {"model": "test"})
    assert credential.payload.artifacts[0].digest.value == sha256_file(artifact)
    sidecar = provider.save_credential(artifact, credential)
    assert sidecar == credential_path_for_artifact(artifact)
    assert read_sidecar(artifact) == credential
    with pytest.raises(CredentialError, match="already exists"):
        provider.save_credential(artifact, credential)
    provider.save_credential(artifact, credential, overwrite=True)


def test_provider_rejects_key_mismatch(provider):
    class WrongSigner:
        key_id = "wrong"

        def sign(self, payload):
            return b"x"

    with pytest.raises(KeyError, match="active key"):
        GapProvider(provider.identity, WrongSigner())
    assert "private" not in repr(provider)


def test_verifier_cryptographic_level_is_explicit(provider):
    artifact = b"valid"
    credential = provider.issue_credential(artifact, {"model": "test"})
    state = {"providers": [provider.identity.model_dump(mode="json")]}
    material = {
        "manifest": {
            "format": "gap-public-state-v1",
            "sha256": hashlib.sha256(canonical_json(state)).hexdigest(),
        },
        "state": state,
    }
    verifier = GapVerifier.from_trust_material(material)
    result = verifier.verify(
        artifact, credential, level=VerificationLevel.CRYPTOGRAPHIC
    )
    assert result.valid
    assert result.achieved_level == VerificationLevel.CRYPTOGRAPHIC
    incomplete = verifier.verify(artifact, credential)
    assert not incomplete.valid
    assert incomplete.failure_code == "incomplete-verification"
    assert incomplete.achieved_level == VerificationLevel.CRYPTOGRAPHIC


def test_verifier_detects_tampering(provider):
    credential = provider.issue_credential(b"valid", {"model": "test"})
    state = {"providers": [provider.identity.model_dump(mode="json")]}
    material = {
        "manifest": {"sha256": hashlib.sha256(canonical_json(state)).hexdigest()},
        "state": state,
    }
    result = GapVerifier.from_trust_material(material).verify(
        b"tampered", credential, level=VerificationLevel.CRYPTOGRAPHIC
    )
    assert not result.valid
    assert result.failure_code == "artifact-digest"


def test_trust_material_deterministic_digest_and_tamper(tmp_path):
    path = tmp_path / "trust.json"
    state = {"providers": [], "signed_tree_heads": []}
    save_trust_material(state, path)
    assert load_trust_material(path).state == state
    raw = json.loads(path.read_text("utf-8"))
    raw["state"]["providers"].append({"provider_id": "tampered"})
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(TrustMaterialError, match="digest"):
        load_trust_material(path)


def test_service_client_headers_envelope_and_errors(provider):
    credential = provider.issue_credential(b"x", {"model": "test"})

    def handler(request):
        assert request.headers["user-agent"].startswith("gap-python-sdk/")
        assert json.loads(request.content)["credential"]["payload"]
        return httpx.Response(200, json={"cryptographic_valid": True})

    client = GapServiceClient(
        "https://gap.example/", transport=httpx.MockTransport(handler)
    )
    assert client.base_url == "https://gap.example"
    assert client.verify_credential(credential)["cryptographic_valid"]
    malformed = GapServiceClient(
        "https://gap.example",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="no")),
    )
    with pytest.raises(ServiceError, match="malformed JSON"):
        malformed.health()


def test_administrative_client_repr_redacts_token():
    client = GapAdministrativeClient(
        "https://gap.example",
        "super-secret",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})),
    )
    assert "super-secret" not in repr(client)
