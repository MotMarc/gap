# Interoperability

GAP 0.16 implements `gap-interop-v1`; the normative declaration is
`protocol/GAP-Interop-Profile-v1.md`. Clients discover a service through
`GET /.well-known/gap.json` and require an exact compatible profile, schema,
digest, binding, trust format, and requested verification level. Discovery
metadata is not a trust root and stale or malicious discovery can only cause
refusal, never establish trust.

Sidecars remain the simplest raw-byte transport. `.gapbundle` packages carry an
artifact and credential together and can optionally carry public trust material.
PNG can carry a credential natively. Other media uses sidecars or packages.
Unknown profiles and attempted embedded-to-raw downgrades fail closed.

## Cross-installation verification

`scripts/validate_cross_installation.py` creates two temporary persisted
installations. Instance A is the issuer and public trust source. Instance B is a
separate portable verifier process with a distinct SQLite database, runtime
directory, port, application object and process memory. Only artifacts,
credentials, packages, embedded PNGs and exported public trust material cross
the boundary. Instance B validates that material statelessly and never imports
it into persistent trust state. Both databases are restarted and checked.
