from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def redact(value: str) -> str:
    return value.replace(str(ROOT), "<repository>").replace(str(Path.home()), "<home>")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    value.update(path.read_bytes())
    return value.hexdigest()


def database_snapshot(path: Path) -> dict:
    with sqlite3.connect(path) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            if not row[0].startswith("sqlite_")
        ]
        counts = {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in tables
        }
    return {"sha256": digest(path), "table_counts": counts}


def start_service(env: dict[str, str], port: int):
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--app-dir",
            "implementation",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("isolated GAP service exited before readiness")
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health/ready", timeout=1
            ) as response:
                if response.status == 200:
                    return process
        except OSError:
            time.sleep(0.1)
    process.terminate()
    raise RuntimeError("isolated GAP service readiness timed out")


def stop_service(process) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run() -> dict:
    run_id = uuid.uuid4().hex
    root = ROOT / "release-output" / f"backup-rehearsal-{run_id}"
    source = root / "source.sqlite3"
    restored = root / "restored.sqlite3"
    backup_dir = root / "backup"
    root.mkdir(parents=True)
    base_env = os.environ.copy()
    base_env.update(
        {
            "APP_ENV": "demonstration",
            "APP_VERSION": "1.0.0",
            "PERSISTENCE_MODE": "database",
            "RUNTIME_DIRECTORY": str(root / "runtime"),
            "BACKUP_DIRECTORY": str(backup_dir),
            "KEY_DIRECTORY": str(ROOT / "implementation" / "keys"),
        }
    )
    try:
        source_env = {**base_env, "DATABASE_URL": f"sqlite:///{source.as_posix()}"}
        subprocess.run(
            [sys.executable, "scripts/manage_database.py", "upgrade"],
            cwd=ROOT,
            env=source_env,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        from gap_sdk import (
            GapProvider,
            GapServiceClient,
            GapVerifier,
            VerificationLevel,
        )
        from gap_sdk.models import ProviderIdentity

        artifact = b"GAP isolated backup rehearsal artifact"
        service = start_service(source_env, 8791)
        try:
            client = GapServiceClient("http://127.0.0.1:8791")
            identity = ProviderIdentity.model_validate(
                client.get_provider("gap-demo-provider")
            )
            provider = GapProvider.from_key_file(
                identity, ROOT / "implementation/keys/demo_2026_02_private.key"
            )
            credential = provider.issue_credential(
                artifact, {"model": "backup-rehearsal"}
            )
            before_verification = GapVerifier.from_service(
                "http://127.0.0.1:8791"
            ).verify(artifact, credential, level=VerificationLevel.FULL)
        finally:
            stop_service(service)
        created = subprocess.run(
            [
                sys.executable,
                "scripts/backup_persistent_state.py",
                "--output",
                str(backup_dir),
            ],
            cwd=ROOT,
            env=source_env,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        manifest_path = next(backup_dir.glob("*.manifest.json"))
        manifest = json.loads(manifest_path.read_text("utf-8"))
        backup_file = backup_dir / manifest["database_file"]
        backup_point = database_snapshot(backup_file)
        verified = (
            subprocess.run(
                [
                    sys.executable,
                    "scripts/backup_persistent_state.py",
                    "--verify",
                    str(manifest_path),
                ],
                cwd=ROOT,
                env=source_env,
                capture_output=True,
                text=True,
                timeout=30,
            ).returncode
            == 0
        )
        with sqlite3.connect(source) as connection:
            connection.execute("CREATE TABLE post_backup_probe(value TEXT NOT NULL)")
            connection.execute(
                "INSERT INTO post_backup_probe VALUES ('must-not-restore')"
            )
        after = database_snapshot(source)
        source_after_digest = after["sha256"]
        no_confirmation = subprocess.run(
            [sys.executable, "scripts/restore_persistent_state.py", str(manifest_path)],
            cwd=ROOT,
            env={**base_env, "DATABASE_URL": f"sqlite:///{restored.as_posix()}"},
            capture_output=True,
            text=True,
            timeout=30,
        )
        restore = subprocess.run(
            [
                sys.executable,
                "scripts/restore_persistent_state.py",
                str(manifest_path),
                "--confirm-restore",
            ],
            cwd=ROOT,
            env={**base_env, "DATABASE_URL": f"sqlite:///{restored.as_posix()}"},
            capture_output=True,
            text=True,
            timeout=30,
        )
        restored_snapshot = database_snapshot(restored)
        restored_service = start_service(
            {**base_env, "DATABASE_URL": f"sqlite:///{restored.as_posix()}"}, 8792
        )
        try:
            restored_verification = GapVerifier.from_service(
                "http://127.0.0.1:8792"
            ).verify(artifact, credential, level=VerificationLevel.FULL)
        finally:
            stop_service(restored_service)
        with sqlite3.connect(restored) as connection:
            post_backup_absent = (
                connection.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='post_backup_probe'"
                ).fetchone()[0]
                == 0
            )
        tampered = backup_dir / "tampered.sqlite3"
        shutil.copyfile(backup_file, tampered)
        with tampered.open("ab") as handle:
            handle.write(b"tamper")
        tampered_manifest = dict(manifest, database_file=tampered.name)
        tampered_manifest_path = backup_dir / "tampered.manifest.json"
        tampered_manifest_path.write_text(
            json.dumps(tampered_manifest, sort_keys=True), "utf-8"
        )
        corrupted_rejected = (
            subprocess.run(
                [
                    sys.executable,
                    "scripts/backup_persistent_state.py",
                    "--verify",
                    str(tampered_manifest_path),
                ],
                cwd=ROOT,
                env=source_env,
                capture_output=True,
                text=True,
                timeout=30,
            ).returncode
            != 0
        )
        secret_scan = backup_file.read_bytes()
        safe = (
            b"PRIVATE KEY" not in secret_scan and b"ADMIN_API_TOKEN" not in secret_scan
        )
        report = {
            "format": "gap-backup-restore-rehearsal-v1",
            "version": "1.0.0",
            "backup_created": created.returncode == 0,
            "backup_verified": verified,
            "manifest": {
                "migration_revision": manifest["migration_revision"],
                "database_type": manifest["database_type"],
                "digest_present": len(manifest["sha256"]) == 64,
                "includes_private_keys": manifest["includes_private_keys"],
            },
            "backup_point": backup_point,
            "post_backup_state_differs": backup_point["sha256"] != after["sha256"],
            "restore_confirmation_enforced": no_confirmation.returncode == 2,
            "restore_succeeded": restore.returncode == 0,
            "restored_state_equivalent": restored_snapshot == backup_point,
            "original_artifact_full_before_backup": before_verification.valid,
            "original_artifact_full_after_restore": restored_verification.valid,
            "post_backup_state_absent": post_backup_absent,
            "corrupted_backup_rejected": corrupted_rejected,
            "key_and_secret_exclusion": safe,
            "source_database_preserved": digest(source) == source_after_digest,
        }
        report["passed"] = all(
            value
            for key, value in report.items()
            if key
            in {
                "backup_created",
                "backup_verified",
                "post_backup_state_differs",
                "restore_confirmation_enforced",
                "restore_succeeded",
                "restored_state_equivalent",
                "original_artifact_full_before_backup",
                "original_artifact_full_after_restore",
                "post_backup_state_absent",
                "corrupted_backup_rejected",
                "key_and_secret_exclusion",
                "source_database_preserved",
            }
        )
        if report["passed"]:
            shutil.rmtree(root, ignore_errors=True)
        return report
    except Exception as exc:
        return {
            "format": "gap-backup-restore-rehearsal-v1",
            "passed": False,
            "error": redact(str(exc)),
            "evidence_location": redact(str(root)),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, "utf-8")
    print(
        encoded
        if args.json
        else f"backup/restore rehearsal: {'passed' if report['passed'] else 'failed'}"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
