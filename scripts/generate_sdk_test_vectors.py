import argparse
import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "implementation"))
from app.crypto.canonical_json import canonicalise_model  # noqa: E402
from app.crypto.provider_keys import encode_public_key  # noqa: E402
from app.schemas.artifact import ArtifactDescriptor, ArtifactDigest  # noqa: E402
from app.schemas.generation_credential import (  # noqa: E402
    CredentialGeneration,
    CredentialModel,
    CredentialProvider,
    GenerationCredential,
    GenerationCredentialPayload,
    GenerationCredentialProof,
)
from gap_sdk.version import __version__  # noqa: E402


OUTPUT = ROOT / "protocol" / "test-vectors" / "v0.15"
TEST_PRIVATE_SEED = bytes(range(1, 33))


def build() -> dict[str, str]:
    artifact = b"GAP Sprint 15 deterministic TEST ONLY artifact\n"
    private = Ed25519PrivateKey.from_private_bytes(TEST_PRIVATE_SEED)
    payload = GenerationCredentialPayload(
        credential_id="gc-test-only-sprint15-valid",
        generation=CredentialGeneration(
            generation_id="gid-test-only-sprint15",
            created_at=datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc),
        ),
        provider=CredentialProvider(provider_id="gap-test-only-vector-provider"),
        model=CredentialModel(model_id="gap-test-only-vector-model"),
        artifacts=[
            ArtifactDescriptor(
                media_type="text/plain",
                digest=ArtifactDigest(value=hashlib.sha256(artifact).hexdigest()),
            )
        ],
    )
    credential = GenerationCredential(
        payload=payload,
        proof=GenerationCredentialProof(
            key_id="gap-test-only-vector-key",
            signature=base64.b64encode(
                private.sign(canonicalise_model(payload))
            ).decode(),
        ),
    )
    identity = {
        "gap_version": "0.0.1",
        "provider_id": "gap-test-only-vector-provider",
        "provider_name": "GAP TEST ONLY Vector Provider",
        "active_key_id": "gap-test-only-vector-key",
        "keys": [
            {
                "key_id": "gap-test-only-vector-key",
                "algorithm": "Ed25519",
                "public_key": encode_public_key(private.public_key()),
                "status": "active",
                "created_at": "2026-07-29T12:00:00Z",
            }
        ],
    }
    files = {
        "artifact.txt": artifact.decode(),
        "credential.json": dump(credential.model_dump(mode="json")),
        "provider-identity.json": dump(identity),
        "expected.json": dump(
            {
                "valid_artifact": {
                    "artifact_integrity_valid": True,
                    "cryptographic_valid": True,
                    "overall_cryptographic_valid": True,
                },
                "tampered_artifact": {
                    "artifact_integrity_valid": False,
                    "cryptographic_valid": True,
                    "overall_cryptographic_valid": False,
                },
            }
        ),
    }
    scenarios = {
        "valid-text-artifact": (True, None),
        "valid-binary-artifact": (True, None),
        "artifact-tampered": (False, "artifact-digest"),
        "credential-payload-tampered": (False, "invalid-signature"),
        "signature-tampered": (False, "invalid-signature"),
        "unknown-provider": (False, "unknown-provider"),
        "retired-key-historical": (True, None),
        "revoked-key": (False, "revoked-key"),
        "provider-suspended": (False, "provider-untrusted"),
        "registry-authority-untrusted": (False, "unknown-registry-authority"),
        "federation-conflict": (False, "federation-conflict"),
        "transparency-inclusion-valid": (True, None),
        "inclusion-proof-invalid": (False, "inclusion-proof-failed"),
        "consistency-proof-invalid": (False, "consistency-proof-failed"),
        "witness-quorum-met": (True, None),
        "witness-quorum-missing": (False, "insufficient-witness-quorum"),
        "split-view": (False, "split-view-detected"),
        "witness-equivocation": (False, "witness-equivocation-detected"),
        "trust-material-stale": (False, "stale-trust-material"),
        "cryptographic-only-incomplete": (False, "incomplete-verification"),
    }
    public_identity = identity
    public_credential = credential.model_dump(mode="json")
    for name, (valid, failure) in scenarios.items():
        files[f"vector-{name}.json"] = dump(
            {
                "format": "gap-test-vector-v1",
                "version": __version__,
                "label": "TEST KEYS ONLY",
                "scenario": name,
                "artifact_sha256": hashlib.sha256(artifact).hexdigest(),
                "artifact_base64": base64.b64encode(artifact).decode(),
                "credential": public_credential,
                "trust_material": {
                    "supported_maximum_verification_level": (
                        "cryptographic"
                        if name == "cryptographic-only-incomplete"
                        else "full"
                    ),
                    "providers": [public_identity],
                    "test_keys_only": True,
                },
                "expected": {
                    "valid": valid,
                    "failure_code": failure,
                },
            }
        )
    manifest = {
        "format": "gap-test-vectors-v1",
        "sdk_version": __version__,
        "test_keys_only": True,
        "files": {
            name: hashlib.sha256(content.encode()).hexdigest()
            for name, content in sorted(files.items())
        },
    }
    files["manifest.json"] = dump(manifest)
    return files


def dump(value) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    if args.check:
        drift = [
            name
            for name, content in expected.items()
            if not (OUTPUT / name).exists()
            or (OUTPUT / name).read_text("utf-8") != content
        ]
        if drift:
            print("vector drift: " + ", ".join(drift))
            return 1
        print(f"{len(expected)} deterministic vector files verified")
        return 0
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, content in expected.items():
        (OUTPUT / name).write_text(content, encoding="utf-8", newline="\n")
    print(f"wrote {len(expected)} deterministic vector files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
