# Operations

`GET /health/live` proves only that the process can answer HTTP. `GET
/health/ready` returns 503 until startup checks complete. The compatibility
`GET /health` endpoint includes bounded, non-secret service counters.

Logs are newline-delimited JSON. Request IDs are accepted from
`X-Request-ID` only when syntactically safe; otherwise the service replaces
them. Every response returns the effective request ID. Error envelopes contain
an error code, safe message and request ID, never a traceback or SQL error.
Known secret fields are redacted and prompts/private attribution records are
not normally logged.

Useful checks:

```powershell
.\.venv\Scripts\python.exe scripts\manage_database.py current
.\.venv\Scripts\python.exe scripts\bootstrap_status.py
.\.venv\Scripts\python.exe scripts\audit_persistent_state.py
.\.venv\Scripts\python.exe scripts\export_public_state.py public-state.json
```

The persistent-state audit verifies migration state, chronology, attestation
bindings, leaf order, Merkle root and orphan indicators. It returns non-zero
and does not repair state. Bootstrap uses stable IDs/timestamps, skips exact
existing records, and fails on incompatible seeded data in strict mode.

Current operational limits include one application process, no distributed
transaction coordinator, no HA/replication, pilot-grade local bearer-token
administration, manual federation/gossip transport, and file-mounted keys.
Production key custody should use a KMS or HSM.

