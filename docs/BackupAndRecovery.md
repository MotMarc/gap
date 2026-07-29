# Backup and recovery

Database backup does not replace key backup. Preserve file-mounted signing
keys separately with stricter access control; a database restored without the
matching keys may verify history but cannot safely sign new state.

SQLite uses the online backup API and a SHA-256 manifest:

```powershell
.\.venv\Scripts\python.exe scripts\backup_persistent_state.py
.\.venv\Scripts\python.exe scripts\backup_persistent_state.py --verify runtime/backups/<backup>.manifest.json
```

Stop the service before restoration. Restoration refuses an invalid digest and
requires explicit confirmation:

```powershell
.\.venv\Scripts\python.exe scripts\restore_persistent_state.py runtime/backups/<backup>.manifest.json --confirm-restore
```

After restore, run migrations in status-only mode and the persistent-state
audit before starting the service. Compare the restored tree size/root and
signed checkpoint with the pre-restore manifest or separately retained public
evidence. Restoring an old but authentic backup is still a rollback risk.

For PostgreSQL, use access-controlled `pg_dump --format=custom`, hash the
result into an external manifest, verify before restore, stop writers, and use
`pg_restore` into a newly created target database. The bundled tool does not
invoke external database commands automatically. Encrypt backup storage,
restrict volume permissions and test recovery regularly.
## Automated v1 rehearsal

Run `python scripts/validate_backup_restore.py --json`. It creates an isolated
SQLite database under ignored release output, invokes the existing backup and
restore commands, verifies the manifest and schema revision, enforces explicit
restore confirmation, excludes post-backup state, compares the restored backup
point, rejects corruption, checks key/token exclusion, and preserves the source.
Successful temporary state is cleaned up; safe diagnostic evidence is retained
on failure.

