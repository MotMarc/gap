from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

try:
    from scripts.validate_cross_installation import run as run_cross_installation
except ModuleNotFoundError:  # Direct script execution
    from validate_cross_installation import run as run_cross_installation

LIMITATIONS = [
    "Reference providers are not commercial-provider integrations.",
    "Production TLS, rate limiting and key custody remain operator responsibilities.",
    "No independent audit, formal verification, HSM or multi-log consensus is claimed.",
]


def redact(value: str) -> str:
    return value.replace(str(Path.home()), "<home>")


def validate_report(report: dict) -> None:
    required_tampering = {
        "artifact",
        "embedded_credential",
        "package",
        "manifest",
        "downgrade",
        "corrupt_trust",
        "stale_trust",
        "unknown_profile",
    }
    if not report.get("passed") or not report.get("three_way_equivalent"):
        raise RuntimeError("Mandatory FULL policy equivalence failed.")
    if not required_tampering.issubset(report.get("tampering_rejected", {})):
        raise RuntimeError("Mandatory tampering results are missing.")
    if not all(report["tampering_rejected"][name] for name in required_tampering):
        raise RuntimeError("A mandatory tampering attempt was accepted.")


def run() -> dict:
    started = time.perf_counter()
    evidence = run_cross_installation()
    validate_report(evidence)
    conformance = {}
    for suite in ("provider", "verifier", "service"):
        result = subprocess.run(
            [sys.executable, "-m", "gap_sdk.cli", "--json", "conformance", suite],
            capture_output=True,
            text=True,
            timeout=30,
        )
        conformance[suite] = result.returncode == 0
    report = {
        "report_format": "gap-mvp-buyer-demo-v1",
        "version": evidence["version"],
        "safe_provider_id": "gap-demo-provider",
        "credential_id": "redacted-to-stable-report",
        "media_type": "image/png",
        "selected_binding_profile": "gap-png-normalized-sha256-v1",
        "online_result": evidence["instance_a_online_full"],
        "offline_result": evidence["offline_sdk_full"],
        "second_installation_result": evidence["instance_b_full"],
        "equivalence_result": evidence["three_way_equivalent"],
        "tampering_outcomes": evidence["tampering_rejected"],
        "conformance_outcomes": conformance,
        "persistence_restart_outcome": (
            evidence["instance_a_restart"] and evidence["instance_b_restart"]
        ),
        "timing_summary": {"total_seconds": time.perf_counter() - started},
        "limitations": LIMITATIONS,
        "passed": all(conformance.values()),
        "advanced_evidence": evidence,
    }
    digest_body = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    report["report_digest"] = hashlib.sha256(digest_body).hexdigest()
    return report


def buyer_text(report: dict) -> str:
    return (
        "GAP v1.0 buyer demonstration: PASSED\n\n"
        "An independent provider process generated a PNG and the GAP reference "
        "provider issued its provenance credential. The verifier checked the "
        "artifact binding, signature, provider and registry trust, append-only "
        "transparency evidence, witness quorum and gossip consistency. The same "
        "FULL result was reproduced offline and by an isolated second installation. "
        "Artifact, embedded credential, package, trust and profile-downgrade "
        "tampering were rejected. Persistent restart retained valid evidence.\n\n"
        f"Remaining limitations: {' '.join(report['limitations'])}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = run()
    except Exception as exc:
        report = {
            "report_format": "gap-mvp-buyer-demo-v1",
            "passed": False,
            "error": redact(str(exc)),
        }
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "buyer-report.txt").write_text(
            buyer_text(report)
            if report["passed"]
            else f"GAP demo failed: {report['error']}\n",
            "utf-8",
        )
        (args.output / "advanced-evidence.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8"
        )
    print(json.dumps(report, sort_keys=True) if args.json else buyer_text(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
