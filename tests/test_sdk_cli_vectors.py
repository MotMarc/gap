import hashlib
import json
from pathlib import Path

from gap_sdk.cli import EXIT_MALFORMED, EXIT_VALID, main
from gap_sdk.models import GapCredential, ProviderIdentity
from gap_sdk.verifier import GapVerifier
from gap_sdk.models import VerificationLevel


ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "protocol" / "test-vectors" / "v0.15"


def test_cli_version_json(capsys):
    assert main(["--json", "version"]) == EXIT_VALID
    assert json.loads(capsys.readouterr().out)["version"] == "1.0.0"


def test_cli_malformed_credential_has_no_traceback(tmp_path, capsys):
    malformed = tmp_path / "bad.json"
    malformed.write_text("{", encoding="utf-8")
    assert main(["credential-inspect", str(malformed)]) == EXIT_MALFORMED
    assert "Traceback" not in capsys.readouterr().err


def test_vectors_parse_verify_and_manifest():
    manifest = json.loads((VECTORS / "manifest.json").read_text("utf-8"))
    assert manifest["test_keys_only"] is True
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((VECTORS / name).read_bytes()).hexdigest() == expected
    identity = ProviderIdentity.model_validate_json(
        (VECTORS / "provider-identity.json").read_text("utf-8")
    )
    credential = GapCredential.model_validate_json(
        (VECTORS / "credential.json").read_text("utf-8")
    )
    state = {"providers": [identity.model_dump(mode="json")]}
    material = {
        "manifest": {
            "sha256": hashlib.sha256(
                json.dumps(
                    state,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode()
            ).hexdigest()
        },
        "state": state,
    }
    result = GapVerifier.from_trust_material(material).verify(
        (VECTORS / "artifact.txt").read_bytes(),
        credential,
        level=VerificationLevel.CRYPTOGRAPHIC,
    )
    assert result.valid


def test_vector_generator_check():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "scripts/generate_sdk_test_vectors.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "25 deterministic vector files verified" in result.stdout
