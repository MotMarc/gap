import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "implementation"))
from app.core.settings import get_settings  # noqa: E402


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore a verified SQLite GAP backup."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--confirm-restore", action="store_true")
    args = parser.parse_args()
    if not args.confirm_restore:
        print(
            "Restore refused: pass --confirm-restore after stopping the service.",
            file=sys.stderr,
        )
        return 2
    settings = get_settings()
    if not settings.database_url.startswith("sqlite"):
        print("Use the documented pg_restore workflow for PostgreSQL.", file=sys.stderr)
        return 2
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    backup = args.manifest.parent / manifest["database_file"]
    if not backup.is_file() or digest(backup) != manifest["sha256"]:
        print("Restore refused: backup digest verification failed.", file=sys.stderr)
        return 1
    parsed = urlparse(settings.database_url)
    target = Path(
        parsed.path.lstrip("/") if sys.platform == "win32" else parsed.path
    ).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, target)
    print(f"restored_backup_id={manifest['backup_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
