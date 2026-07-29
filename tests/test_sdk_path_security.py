import hashlib
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.crypto.provider_keys import encode_public_key
from gap_sdk import (
    PNG_BINDING,
    RAW_BINDING,
    GapProvider,
    GapVerifier,
    VerificationLevel,
)
from gap_sdk.errors import CredentialError
from gap_sdk.files import resolve_local_file, sha256_file
from gap_sdk.models import ProviderIdentity


@pytest.fixture
def provider():
    private = Ed25519PrivateKey.generate()
    identity = ProviderIdentity(
        provider_id="path-security-provider",
        provider_name="Path Security Provider",
        active_key_id="path-security-key",
        keys=[
            {
                "key_id": "path-security-key",
                "public_key": encode_public_key(private.public_key()),
                "status": "active",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    class Signer:
        key_id = "path-security-key"
        public_key_base64 = encode_public_key(private.public_key())

        def sign(self, payload):
            return private.sign(payload)

    return GapProvider(identity, Signer())


def _credential(provider, artifact: bytes, *, png: bool = False):
    return provider.issue_credential(
        artifact,
        {"model": "path-security", "media_type": "image/png" if png else "text/plain"},
        binding_profile=PNG_BINDING if png else RAW_BINDING,
    )


@pytest.mark.parametrize("value", ["", "\x00", "artifact\x00.bin"])
def test_local_file_boundary_rejects_empty_and_null_paths(value):
    with pytest.raises(CredentialError, match="invalid") as caught:
        resolve_local_file(value)
    assert str(Path.cwd()) not in str(caught.value)


def test_local_file_boundary_rejects_a_directory_without_path_disclosure(tmp_path):
    with pytest.raises(CredentialError, match="must identify a file") as caught:
        resolve_local_file(tmp_path)
    assert str(tmp_path) not in str(caught.value)


def test_sha256_file_supports_caller_selected_absolute_and_parent_paths(
    tmp_path, monkeypatch
):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"caller-selected")
    nested = tmp_path / "nested"
    nested.mkdir()
    monkeypatch.chdir(nested)

    expected = hashlib.sha256(b"caller-selected").hexdigest()
    assert sha256_file(artifact.resolve()) == expected
    assert sha256_file(Path("..") / artifact.name) == expected


def test_local_file_boundary_rejects_missing_cross_platform_path_forms():
    values = [
        "../secret",
        r"..\secret",
        "../../nested/secret",
        "/etc/passwd/does-not-exist",
        r"C:\does-not-exist\secret",
        "C:drive-qualified",
        r"\\server\share\secret",
        r"nested\..\secret",
    ]
    for value in values:
        with pytest.raises(CredentialError, match="could not be opened"):
            resolve_local_file(value)


def test_verify_bytes_cannot_turn_credential_data_into_a_file_read(
    provider, tmp_path, monkeypatch
):
    artifact = b"artifact bytes"
    credential = _credential(provider, artifact)
    secret = tmp_path / "secret"
    secret.write_bytes(b"secret")

    def unexpected_path_access(_path):
        raise AssertionError("bytes verification attempted filesystem access")

    monkeypatch.setattr("gap_sdk.verifier.resolve_local_file", unexpected_path_access)
    result = GapVerifier().verify_bytes(
        artifact, credential, level=VerificationLevel.CRYPTOGRAPHIC
    )
    assert result.artifact_integrity_valid
    with pytest.raises(TypeError, match="must be bytes"):
        GapVerifier().verify_bytes(str(secret), credential)


def test_verify_file_is_explicit_and_legacy_verify_path_remains_compatible(
    provider, tmp_path
):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"artifact bytes")
    credential = _credential(provider, artifact.read_bytes())
    verifier = GapVerifier()

    explicit = verifier.verify_file(
        artifact, credential, level=VerificationLevel.CRYPTOGRAPHIC
    )
    compatible = verifier.verify(
        artifact, credential, level=VerificationLevel.CRYPTOGRAPHIC
    )
    assert explicit.artifact_integrity_valid
    assert compatible.artifact_integrity_valid


def test_local_file_symlink_is_resolved_only_for_caller_selected_files(tmp_path):
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"outside")
    link = tmp_path / "link.bin"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable")

    assert resolve_local_file(link) == outside.resolve()
    assert sha256_file(link) == hashlib.sha256(b"outside").hexdigest()
