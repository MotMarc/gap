from __future__ import annotations

import re

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib
from pathlib import Path

from app.core.version import APPLICATION_VERSION
from gap_sdk.version import __version__

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "1.0.0"


def main() -> int:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))
    values = {
        "application": APPLICATION_VERSION,
        "sdk": __version__,
        "package": pyproject["project"]["version"],
    }
    for name in ("Dockerfile", "docker-compose.yml", ".env.example"):
        text = (ROOT / name).read_text("utf-8")
        if not re.search(r"(?<!\d)1\.0\.0(?!\d)", text):
            raise RuntimeError(f"{name} does not declare {EXPECTED}")
    if set(values.values()) != {EXPECTED}:
        raise RuntimeError(f"Version mismatch: {values}")
    print(f"version consistency verified: {EXPECTED}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
