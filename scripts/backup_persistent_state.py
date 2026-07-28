import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "implementation"))
from app.core.settings import get_settings  # noqa: E402
from app.database.engine import create_database_engine  # noqa: E402
from app.database.migrations import current_revision  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or verify a GAP database backup."
    )
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        manifest = json.loads(args.verify.read_text(encoding="utf-8"))
        backup = args.verify.parent / manifest["database_file"]
        valid = backup.is_file() and sha256(backup) == manifest["sha256"]
        print(
            f"backup_valid={str(valid).lower()} backup_id={manifest.get('backup_id', 'unknown')}"
        )
        return 0 if valid else 1

    settings = get_settings()
    if not settings.database_url.startswith("sqlite"):
        print(
            "PostgreSQL backups require pg_dump; see docs/BackupAndRecovery.md.",
            file=sys.stderr,
        )
        return 2
    source = Path(
        urlparse(settings.database_url).path.lstrip("/")
        if sys.platform == "win32"
        else urlparse(settings.database_url).path
    )
    source = source.resolve()
    if not source.is_file():
        print("Database does not exist.", file=sys.stderr)
        return 1
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination_dir = (args.output or settings.backup_directory).resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    backup_id = f"gap-backup-{stamp}"
    destination = destination_dir / f"{backup_id}.sqlite3"
    with (
        sqlite3.connect(source) as source_db,
        sqlite3.connect(destination) as target_db,
    ):
        source_db.backup(target_db)
    engine = create_database_engine(settings.database_url)
    revision = current_revision(engine)
    engine.dispose()
    manifest = {
        "backup_id": backup_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database_file": destination.name,
        "database_type": "sqlite",
        "migration_revision": revision,
        "sha256": sha256(destination),
        "includes_private_keys": False,
    }
    manifest_path = destination.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"backup={destination.name} manifest={manifest_path.name} sha256={manifest['sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
