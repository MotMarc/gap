# Protocol invariants

- Canonical serialisation is deterministic UTF-8; floating point is rejected.
- A credential signature binds its complete payload, including binding profile.
- Callers cannot override a signed profile; the artifact digest must match it.
- Provider keys must be valid at issuance; revocation fails under current policy.
- Trust decisions and transparency leaves are append-only and ordered.
- Federation cannot roll back; conflicts fail closed.
- Tree heads bind root, size and log identity; consistency binds old/new roots.
- Witnesses bind an exact checkpoint; equivocation and split views fail closed.
- Stale material cannot achieve current FULL; skipped checks never pass.
- Requested FULL never silently downgrades.
- Package integrity never substitutes for credential authenticity.
- Discovery is not a trust root; private keys are never public protocol data.
- Restart cannot change cryptographic history.
