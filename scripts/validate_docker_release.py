from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def classify() -> dict:
    docker = shutil.which("docker")
    if not docker:
        return {
            "format": "gap-docker-release-validation-v1",
            "status": "blocked",
            "passed": False,
            "reason": "docker executable was not found on PATH",
            "owner_approval_required": True,
            "validation_command": "python scripts/validate_docker_release.py --json",
        }
    checks = {}
    for name, command in {
        "docker-version": [docker, "version"],
        "compose-version": [docker, "compose", "version"],
        "compose-config": [docker, "compose", "config"],
    }.items():
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        checks[name] = result.returncode == 0
    passed = all(checks.values())
    return {
        "format": "gap-docker-release-validation-v1",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "checks": checks,
        "owner_approval_required": not passed,
        "reason": None if passed else "Docker prerequisite/configuration check failed",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = classify()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, "utf-8")
    print(encoded if args.json else f"Docker validation: {report['status']}")
    return 0 if report["passed"] else 2 if report["status"] == "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
