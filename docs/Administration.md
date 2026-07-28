# Administration

Administrative mutation routes are disabled by default. Set
`ADMIN_API_ENABLED=true` and provide `ADMIN_API_TOKEN_HASH`, the lowercase
SHA-256 digest of a high-entropy token. Never store or pass the plaintext token
in a URL. Use an HTTPS `Authorization: Bearer` header.

```powershell
.\.venv\Scripts\python.exe -c "from app.core.settings import hash_admin_token; print(hash_admin_token('replace-with-random-secret'))" --app-dir implementation
```

The pilot route `POST /admin/providers/{provider_id}/trust` accepts approved,
suspended or removed transitions and delegates to existing domain transition
rules. `GET /admin/audit` returns administrative audit metadata. Successful
and denied mutations record request ID, action, target, outcome, time and a
non-reversible actor fingerprint; tokens and private contacts are excluded.

This mechanism is pilot-grade. It does not provide accounts, roles, OAuth,
token rotation, replay nonces, distributed rate limiting or identity-provider
integration. Restrict network access and require HTTPS.

