# Deployment

## Configuration

Copy `.env.example` only as a reference; the application does not load a
committed `.env`. Configuration is exclusively environmental. Important
variables are `APP_ENV`, `DATABASE_URL`, `PERSISTENCE_MODE`,
`RUNTIME_DIRECTORY`, `KEY_DIRECTORY`, `BACKUP_DIRECTORY`, `LOG_LEVEL`,
`ADMIN_API_ENABLED`, `ADMIN_API_TOKEN_HASH`, `CORS_ALLOWED_ORIGINS`,
`MAX_REQUEST_SIZE`, `STARTUP_STRICT_MODE`, and `HEALTH_DETAILS_ENABLED`.

Production rejects in-memory persistence and wildcard CORS. Enabling the admin
API requires a SHA-256 token digest. Private keys remain mounted files and are
never stored in database rows.

## Local SQLite

```powershell
$env:APP_ENV='development'
$env:PERSISTENCE_MODE='database'
$env:DATABASE_URL='sqlite:///runtime/gap.db'
.\.venv\Scripts\python.exe scripts\manage_database.py upgrade
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir implementation
```

Schema changes are explicit. Startup checks the database revision and never
uses destructive schema recreation. To inspect it:

```powershell
.\.venv\Scripts\python.exe scripts\manage_database.py current
```

For a disposable development reset, stop the service, preserve any evidence
needed for audit, remove only the explicitly selected development SQLite file,
then rerun the migration. There is deliberately no generic production reset.

## Docker Compose

Mount an existing complete key directory; the container never creates keys.

```powershell
$env:POSTGRES_PASSWORD='<strong-local-secret>'
$env:GAP_KEY_DIRECTORY=(Resolve-Path implementation/keys)
docker compose up --build
```

The entrypoint runs the explicit migration command and then `exec`s Uvicorn.
PostgreSQL, runtime and backup data use named volumes. Compose is a
demonstrator/pilot topology, not a high-availability architecture.

The service must be terminated behind HTTPS in any deployment that enables
bearer-token administration.

