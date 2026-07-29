from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.version import APPLICATION_VERSION
from app.crypto.provider_keys import encode_public_key
from app.services.verification_service import verify_generation_credential
from gap_sdk import (
    Ed25519FileSigner,
    GapPackage,
    GapProvider,
    PNG_BINDING,
    embed_credential_in_png,
    extract_credential_from_png,
)
from gap_sdk.models import ProviderIdentity

ROOT = Path(__file__).resolve().parents[1]
REPETITIONS = 3


def redact(value: str) -> str:
    return value.replace(str(ROOT), "<repository>").replace(str(Path.home()), "<home>")


def summarise(samples: list[float]) -> dict[str, float]:
    return {
        "minimum_seconds": min(samples),
        "median_seconds": statistics.median(samples),
        "maximum_seconds": max(samples),
    }


def measure(
    operation: str,
    size: int,
    function: Callable[[], object],
    repetitions: int = REPETITIONS,
) -> dict:
    samples: list[float] = []
    peak = 0
    try:
        for _ in range(repetitions):
            tracemalloc.start()
            started = time.perf_counter()
            function()
            samples.append(time.perf_counter() - started)
            _, current_peak = tracemalloc.get_traced_memory()
            peak = max(peak, current_peak)
            tracemalloc.stop()
        result = {
            "operation": operation,
            "artifact_size_bytes": size,
            **summarise(samples),
            "peak_python_memory_bytes": peak,
            "result": "passed",
        }
        if size:
            result["median_throughput_mib_per_second"] = (
                size / 1024 / 1024 / result["median_seconds"]
            )
        return result
    except Exception as exc:
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        return {
            "operation": operation,
            "artifact_size_bytes": size,
            "result": "failed",
            "error": redact(str(exc)),
        }


def _provider() -> GapProvider:
    private = Ed25519PrivateKey.generate()
    signer = Ed25519FileSigner("benchmark-ephemeral-key", private)
    identity = ProviderIdentity.model_validate(
        {
            "provider_id": "gap-benchmark-ephemeral",
            "provider_name": "GAP benchmark ephemeral provider",
            "active_key_id": signer.key_id,
            "keys": [
                {
                    "key_id": signer.key_id,
                    "public_key": encode_public_key(private.public_key()),
                    "status": "active",
                    "created_at": "2026-01-01T00:00:00Z",
                }
            ],
        }
    )
    return GapProvider(identity, signer)


def run() -> dict:
    provider = _provider()
    payloads = [
        ("small", b"GAP benchmark"),
        ("1mb", bytes(1024 * 1024)),
        ("25mb", bytes(25 * 1024 * 1024)),
    ]
    operations = []
    credentials = {}
    for label, artifact in payloads:
        operations.append(
            measure(
                f"sha256-{label}",
                len(artifact),
                lambda a=artifact: hashlib.sha256(a).digest(),
            )
        )
        operations.append(
            measure(
                f"credential-issuance-{label}",
                len(artifact),
                lambda a=artifact: provider.issue_credential(a, {"model": "benchmark"}),
            )
        )
        credentials[label] = provider.issue_credential(artifact, {"model": "benchmark"})
    small = payloads[0][1]
    credential = credentials["small"]
    operations.append(
        measure(
            "cryptographic-verification",
            len(small),
            lambda: verify_generation_credential(credential, provider.identity),
        )
    )
    package = GapPackage.create(small, credential, artifact_name="artifact.bin")
    operations.extend(
        [
            measure(
                "package-creation",
                len(small),
                lambda: GapPackage.create(
                    small, credential, artifact_name="artifact.bin"
                ),
            ),
            measure(
                "package-integrity-verification",
                len(package),
                lambda: GapPackage.verify_integrity(package),
            ),
        ]
    )
    png = (ROOT / "testgap.png").read_bytes()
    png_credential = provider.issue_credential(
        png,
        {"model": "benchmark", "media_type": "image/png"},
        binding_profile=PNG_BINDING,
    )
    embedded = embed_credential_in_png(png, png_credential)
    operations.extend(
        [
            measure(
                "png-embedding",
                len(png),
                lambda: embed_credential_in_png(png, png_credential),
            ),
            measure(
                "png-extraction",
                len(embedded),
                lambda: extract_credential_from_png(embedded),
            ),
            measure(
                "png-integrity-verification",
                len(embedded),
                lambda: hashlib.sha256(embedded).digest(),
            ),
        ]
    )
    return {
        "format": "gap-mvp-benchmark-v1",
        "version": APPLICATION_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "processor": platform.processor() or "not-reported",
        },
        "repetitions": REPETITIONS,
        "operations": operations,
        "result": "passed"
        if operations and all(item["result"] == "passed" for item in operations)
        else "failed",
        "limitations": [
            "Local single-process reference measurements; not production capacity.",
            "No distributed, multi-region, concurrent-load or external-network test.",
            "FULL verification timings are reported by the authoritative live demo.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, "utf-8")
    print(encoded if args.json else f"benchmark result: {report['result']}")
    return 0 if report["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
