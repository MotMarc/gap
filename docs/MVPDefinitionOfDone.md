# GAP v1.0 MVP definition of done

GAP v1 guarantees that a participating provider can issue an Ed25519-signed
Generation Credential and that a verifier can bind it to raw bytes, a sidecar,
a portable `gap-package-v1` archive, or the signed PNG binding profile.
Online and exported-trust-material offline FULL verification apply the same
provider, registry, federation, transparency, witness, gossip and freshness
policy. A restart-safe SQLite or PostgreSQL deployment preserves cryptographic
history; public export contains public evidence only.

The reference implementation guarantees authenticated administration,
auditing, explicit migrations, backups, deterministic vectors, SDK/CLI
integration, conformance reports, discovery negotiation and non-root Docker
deployment. Operators remain responsible for TLS, rate limiting, access
control, key custody, monitoring, backup protection and database operation.
Providers are responsible for signing-key security and truthful issuance.
Verifiers are responsible for trusted authority configuration, current trust
material and handling failed or incomplete results.

GAP does not guarantee universal provider adoption or media coverage, perfect
anonymity, safety after signing infrastructure compromise, HSM protection,
C2PA compliance, legal certification, formal verification or an independent
security audit. The included providers are reference integrations, not
commercial-vendor validation.

The locally runnable v1 gates passed on 2026-07-29: automated tests, vectors,
API snapshot, clean installation, online/offline/cross-installation FULL
verification, browser validation, backup/restore rehearsal, performance
measurement, conformance, buyer demo and review-package verification. Docker
remains a blocked environmental gate pending validation on a Docker-capable
machine or an explicit owner-approved exception.
