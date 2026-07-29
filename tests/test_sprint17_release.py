from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.crypto.canonical_json import canonical_json, canonicalise_model
from gap_sdk import __version__
from gap_sdk.models import GenerationContext
from gap_sdk.serialization import canonical_json as sdk_canonical_json

ROOT = Path(__file__).resolve().parents[1]


def test_release_version_and_openapi_snapshot_are_frozen() -> None:
    assert __version__ == "1.0.0"
    result = subprocess.run(
        [sys.executable, "scripts/freeze_openapi.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_canonicalisation_golden_and_cross_layer_equivalence() -> None:
    value = {
        "unicode": "é雪",
        "empty": "",
        "nested": {"z": None, "a": [True, False, 7]},
        "timestamp": "2026-01-02T03:04:05+00:00",
    }
    expected = (
        '{"empty":"","nested":{"a":[true,false,7],"z":null},'
        '"timestamp":"2026-01-02T03:04:05+00:00","unicode":"é雪"}'
    ).encode()
    assert canonical_json(value) == expected
    assert sdk_canonical_json(value) == expected


def test_canonicalisation_rejects_floats_at_any_depth() -> None:
    with pytest.raises(TypeError, match="Floating-point"):
        canonical_json({"nested": [1, {"unsafe": 1.5}]})


def test_model_canonicalisation_uses_authoritative_core() -> None:
    model = GenerationContext(model="gap-test")
    assert canonicalise_model(model) == sdk_canonical_json(model)


def test_v1_release_vector_catalogue_is_deterministic_and_labelled() -> None:
    manifest = json.loads(
        (ROOT / "protocol/test-vectors/v1.0/manifest.json").read_text("utf-8")
    )
    assert manifest["warning"] == "TEST KEYS ONLY"
    assert len(manifest["cases"]) == 20
    assert "profile-downgrade" in manifest["cases"]
    assert "malformed-archive" in manifest["cases"]
