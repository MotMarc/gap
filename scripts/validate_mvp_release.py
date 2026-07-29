from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def redact(value: str) -> str:
    return value.replace(str(ROOT), "<repository>").replace(str(Path.home()), "<home>")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true")
    mode.add_argument("--full", action="store_true")
    parser.add_argument("--owner-approve-unavailable-docker", action="store_true")
    parser.add_argument("--owner-exception-justification")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "release-output" / "report.json"
    )
    args = parser.parse_args()
    commands = [
        ("version", ["scripts/validate_version.py"], True),
        (
            "ruff",
            ["-m", "ruff", "check", "implementation", "tests", "scripts", "examples"],
            True,
        ),
        ("protocol-vectors", ["scripts/generate_test_vectors.py", "--check"], True),
        ("sdk-vectors", ["scripts/generate_sdk_test_vectors.py", "--check"], True),
        ("v1-vectors", ["scripts/generate_v1_vectors.py", "--check"], True),
        ("openapi", ["scripts/freeze_openapi.py"], True),
        ("tests", ["-m", "pytest", "-q"], True),
    ]
    if args.full:
        commands.extend(
            [
                ("clean-install", ["scripts/validate_clean_install.py"], True),
                (
                    "cross-installation",
                    ["scripts/validate_cross_installation.py", "--json"],
                    True,
                ),
                (
                    "browser-console",
                    [
                        "scripts/validate_browser_console.py",
                        "--url",
                        "http://127.0.0.1:8780",
                        "--launch-service",
                        "--json",
                    ],
                    True,
                ),
                (
                    "backup-restore",
                    [
                        "scripts/validate_backup_restore.py",
                        "--json",
                        "--output",
                        "release-output/backup-restore.json",
                    ],
                    True,
                ),
                (
                    "performance",
                    [
                        "scripts/benchmark_mvp.py",
                        "--json",
                        "--output",
                        "release-output/benchmark.json",
                    ],
                    True,
                ),
                (
                    "buyer-demo",
                    [
                        "scripts/run_mvp_demo.py",
                        "--json",
                        "--output",
                        "release-output/mvp-demo",
                    ],
                    True,
                ),
                ("review-package", ["scripts/create_review_package.py"], True),
                (
                    "review-package-verify",
                    ["scripts/create_review_package.py", "--verify"],
                    True,
                ),
            ]
        )
    report = {"format": "gap-release-validation-v1", "checks": []}
    for name, tail, mandatory in commands:
        started = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, *tail], cwd=ROOT, text=True, capture_output=True
        )
        report["checks"].append(
            {
                "name": name,
                "status": "passed" if proc.returncode == 0 else "failed",
                "mandatory": mandatory,
                "duration_seconds": time.perf_counter() - started,
                "safe_summary": redact((proc.stdout + proc.stderr)[-4000:]),
                "evidence_location": (
                    "release-output"
                    if name in {"backup-restore", "performance", "buyer-demo"}
                    else None
                ),
            }
        )
    started = time.perf_counter()
    docker = subprocess.run(
        [sys.executable, "scripts/validate_docker_release.py", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    docker_report = json.loads(docker.stdout)
    docker_check = {
        "name": "docker",
        "status": docker_report["status"],
        "mandatory": bool(args.full),
        "duration_seconds": time.perf_counter() - started,
        "safe_summary": docker_report["reason"] or "Docker release checks passed.",
        "evidence_location": None,
        "blocking_reason": docker_report["reason"],
    }
    report["checks"].append(docker_check)
    waived = []
    if (
        docker_check["status"] == "blocked"
        and args.owner_approve_unavailable_docker
        and args.owner_exception_justification
    ):
        waived.append("docker")
    elif (
        args.owner_approve_unavailable_docker and not args.owner_exception_justification
    ):
        parser.error("--owner-exception-justification is required for an exception")
    if waived:
        report["release_disposition"] = "RELEASE WITH OWNER-APPROVED EXCEPTION"
        report["owner_exception"] = {
            "waived_checks": waived,
            "justification": args.owner_exception_justification,
        }
    else:
        report["release_disposition"] = "STANDARD RELEASE VALIDATION"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    blocked = any(
        c["mandatory"] and c["status"] != "passed" and c["name"] not in waived
        for c in report["checks"]
    )
    print(json.dumps(report, indent=2))
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
