from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "protocol" / "test-vectors" / "v1.0"
CASES = [
    "valid-raw-sidecar",
    "valid-package",
    "valid-embedded-png",
    "online-offline-equivalence",
    "artifact-tampered",
    "credential-tampered",
    "package-tampered",
    "png-tampered",
    "unknown-provider",
    "revoked-key",
    "provider-suspended",
    "federation-conflict",
    "invalid-inclusion-proof",
    "invalid-consistency-proof",
    "missing-quorum",
    "split-view",
    "witness-equivocation",
    "stale-trust-material",
    "profile-downgrade",
    "malformed-archive",
]


def document() -> str:
    source = ROOT / "protocol" / "test-vectors" / "v0.15" / "manifest.json"
    return (
        json.dumps(
            {
                "format": "gap-v1-release-vector-catalogue",
                "warning": "TEST KEYS ONLY",
                "historical_catalogue": "../v0.15/manifest.json",
                "historical_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "cases": CASES,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = DIRECTORY / "manifest.json"
    expected = document()
    if args.check:
        ok = target.is_file() and target.read_text("utf-8") == expected
        print(f"{len(CASES)} v1 release-vector cases {'verified' if ok else 'failed'}")
        return 0 if ok else 1
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    target.write_text(expected, "utf-8")
    print(f"generated {len(CASES)} v1 release-vector cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
