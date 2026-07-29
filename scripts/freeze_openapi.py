from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ["APP_ENV"] = "test"
os.environ["PERSISTENCE_MODE"] = "memory"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.main import app  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "protocol" / "openapi-v1.0.json"


def rendered() -> str:
    document = app.openapi()
    document.pop("servers", None)
    return json.dumps(document, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()
    expected = rendered()
    if args.update:
        SNAPSHOT.write_text(expected, "utf-8")
        print(f"updated {SNAPSHOT.relative_to(ROOT)}")
        return 0
    if not SNAPSHOT.is_file() or SNAPSHOT.read_text("utf-8") != expected:
        print("OpenAPI snapshot drifted; review and run --update deliberately.")
        return 1
    print("OpenAPI v1 snapshot verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
