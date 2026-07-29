from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "review-output" / "gap-v1.0-review"
FILES = [
    "README.md",
    "CHANGELOG.md",
    "SECURITY.md",
    "LICENSE",
    "docs/MVPDefinitionOfDone.md",
    "docs/Architecture.md",
    "docs/ThreatModel.md",
    "docs/ProtocolInvariants.md",
    "docs/InternalSecurityReview.md",
    "docs/CompatibilityPolicy.md",
    "docs/Performance.md",
    "docs/DependencyReview.md",
    "docs/KnownLimitations.md",
    "docs/ReleaseProcess.md",
    "protocol/GAP-v1.0.md",
    "protocol/GAP-Interop-Profile-v1.md",
    "protocol/openapi-v1.0.json",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    for relative in FILES:
        source = ROOT / relative
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    manifest = {
        "format": "gap-review-package-v1",
        "source_commit": _commit(),
        "files": {name: digest(output / name) for name in sorted(FILES)},
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", "utf-8"
    )


def _commit() -> str:
    import subprocess

    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def verify(output: Path) -> bool:
    manifest = json.loads((output / "manifest.json").read_text("utf-8"))
    return all(
        digest(output / name) == value for name, value in manifest["files"].items()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        ok = verify(args.output)
    else:
        build(args.output)
        ok = verify(args.output)
    print("review package verified" if ok else "review package verification failed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
