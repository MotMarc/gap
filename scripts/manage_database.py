import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "implementation"))

from app.core.settings import get_settings  # noqa: E402
from app.database.engine import create_database_engine  # noqa: E402
from app.database.migrations import (  # noqa: E402
    HEAD_REVISION,
    current_revision,
    upgrade_to_head,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the GAP database schema.")
    parser.add_argument("command", choices=("upgrade", "current"))
    args = parser.parse_args()
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    try:
        if args.command == "upgrade":
            print(f"migration={upgrade_to_head(engine)}")
        else:
            revision = current_revision(engine)
            print(f"migration={revision or 'uninitialised'} head={HEAD_REVISION}")
            return 0 if revision == HEAD_REVISION else 1
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
