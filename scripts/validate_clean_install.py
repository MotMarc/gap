from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=ROOT, check=True, text=True, **kwargs)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="gap-clean-install-") as temporary:
        root = Path(temporary)
        (root / "dist").mkdir()
        run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                ".",
                "--no-deps",
                "--wheel-dir",
                str(root / "dist"),
            ]
        )
        run([sys.executable, "-m", "venv", str(root / "venv")])
        python = (
            root
            / "venv"
            / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        )
        wheel = next((root / "dist").glob("*.whl"))
        run([str(python), "-m", "pip", "install", str(wheel)], stdout=subprocess.PIPE)
        command = [str(python), "-m", "gap_sdk.cli", "--json", "version"]
        result = subprocess.run(command, cwd=root, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        if json.loads(result.stdout)["version"] != "1.0.0":
            raise RuntimeError("Clean installation reported the wrong version.")
        run([str(python), "-m", "pip", "check"], stdout=subprocess.PIPE)
    print("clean wheel installation verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
