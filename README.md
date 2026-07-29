# Generation Attribution Protocol (GAP)

GAP is an open protocol proposal for privacy-preserving attribution of AI-generated artefacts.

Version 0.16 adds the [interoperability profile](protocol/GAP-Interop-Profile-v1.md),
service discovery, explicit negotiation, portable `.gapbundle` packages, native
PNG binding, and an independent HTTP provider pilot. Other media continues to
use sidecars or packages.

Run instrumented desktop/mobile browser validation with
`.\.venv\Scripts\python.exe scripts\validate_browser_console.py --url
http://127.0.0.1:8780 --launch-service --json`. Run the isolated persisted
two-installation validation with `.\.venv\Scripts\python.exe
scripts\validate_cross_installation.py --json`.

The objective of GAP is to enable participating AI providers to cryptographically associate generated artefacts with a unique Generation Identifier while preserving user privacy by default and supporting lawful attribution under due process.

## Current Status

Early research and reference implementation, version 0.16.0.

Sprint 15 adds the installable Python provider/verifier SDK, typed HTTP client,
atomic credential sidecars, explicit verification levels, offline public-state
loading, the `gap` integration CLI, examples and deterministic test vectors.

Sprint 14 adds typed environment configuration, SQLite/PostgreSQL persistence,
explicit schema migrations, restart-safe bootstrap, authenticated pilot
administration, operational health checks, backups, public-state export and a
non-root Docker deployment. Protocol object versions remain unchanged.

Sprint 13 adds independent Transparency Witness identities and Ed25519
checkpoint statements, configurable witness quorum, and manually exchanged,
file-based checkpoint gossip. The monitor retains conflicting observations and
fails closed on split views, rollback, witness equivocation, invalid
consistency, stale statements, and insufficient quorum.

Sprint 12 adds a dedicated Transparency Log Operator, typed public log entries,
signed Merkle-tree checkpoints, verifiable inclusion proofs and append-only
consistency proofs. A signed provider trust source establishes effective trust
only when its public attestation (or accepted federation bundle) is included in
a trusted signed tree head.

Sprint 10 adds portable Ed25519-signed provider trust-decision attestations.
A provider is trusted only when it is approved, its current decision has a
valid matching attestation, and the issuing registry authority is configured
as trusted by the local verifier.

## Repository Structure

- `implementation/` – FastAPI reference implementation and browser demonstrator
- `implementation/app/` – Domain, service, schema, API and frontend layers
- `implementation/keys/` – Ignored local demonstration key material
- `protocol/` – GAP specification
- `docs/` – Architecture, decisions and threat model
- `scripts/` – Local setup and demonstration scripts
- `tests/` – Test suite

## Signed registry trust

GAP keeps provider identity, provider trust decisions, registry-authority
identity and local federation policy separate:

- A Provider Identity Document proves which signing keys belong to a provider.
  It does not establish provider trust.
- A provider trust decision records an approval, suspension or removal. An
  unsigned decision does not establish production trust.
- A signed trust-decision attestation binds the complete decision to an
  independently identifiable Registry Authority.
- A Registry Authority Identity Document publishes the authority's Ed25519
  verification-key history.
- The local `RegistryAuthorityRepository` determines which authorities this
  verifier accepts. An unknown authority cannot establish trust.

Authority and key identifiers are resolved exactly. Active authority keys may
sign and verify attestations. Retired keys cannot sign new attestations but
preserve historical verification. Revoked keys invalidate every attestation
that references them.

Approved-provider issuance requires both an active provider signing key and a
fully valid signed-registry trust evaluation.

The complete browser verification policy is:

```text
overall_valid =
    artifact_integrity_valid
    AND credential_cryptographic_valid
    AND provider_trusted
    AND trust_attestation_valid
    AND registry_authority_trusted
    AND federation_state_valid
    AND transparency_verified
    AND witness_quorum_met
    AND checkpoint_gossip_consistent
    AND NOT federation_conflict
    AND NOT split_view_detected
    AND NOT witness_equivocation_detected
```

The credential-verification API reports every constituent control separately.
Artifact integrity is calculated by the verifier from the supplied artifact
bytes and the credential's SHA-256 descriptor.

## Public Sprint 10 API

- `GET /registry-authorities`
- `GET /registry-authorities/{authority_id}/.well-known/gap-registry.json`
- `GET /trust-attestations`
- `GET /trust-attestations/{attestation_id}`
- `GET /trust-registry`
- `GET /providers/{provider_id}/trust`
- `POST /credentials/verify`

`GET /trust-attestations` optionally accepts a `provider_id` query parameter.
Public trust responses never contain private onboarding contact references.
Private attribution records remain separately retained and are available only
through the controlled-disclosure workflow.

## Sprint 12 transparency

The reference log uses Ed25519 checkpoints and
`GAP-RFC6962-SHA256-v1`. Its exact hash rules are:

```text
empty_hash = SHA256(b"")
leaf_hash  = SHA256(b"\x00" + canonical_entry_bytes)
node_hash  = SHA256(b"\x01" + left_hash + right_hash)
```

The tree splits at the largest power of two strictly below its size and never
duplicates an odd final leaf. Inclusion proves membership in one checkpoint;
consistency proves append-only extension between checkpoints. Neither validates
the signed trust object itself. Unknown log operators, revoked log keys,
invalid proofs, and same-size/different-root split views fail closed.

Public routes are `GET /transparency/log`, the well-known log identity,
bounded entry and tree-head listings, entry inclusion proofs, consistency
proofs, and stateless POST verification/comparison routes. No public append or
log-administration route exists.

Create or validate the separate log key pair:

```powershell
.\.venv\Scripts\python.exe scripts\generate_transparency_log_keys.py
```

Runtime entries and checkpoints are atomically persisted under ignored
`runtime/transparency/`. The browser's Transparency Log view exposes public
entries, signed checkpoints and proofs without filesystem paths or private
records.

## Sprint 13 witnesses and gossip

A witness statement signs one exact log ID, tree-head ID, tree size, root,
checkpoint timestamp, observation timestamp and optional consistency
reference. It confirms checkpoint observation, not the underlying trust
artifact. Unknown, revoked or stale witnesses do not count; retired keys may
verify history, and a log operator cannot count as its own witness.

Public read/stateless routes are under `/transparency/witnesses`,
`/transparency/witness-statements`, `/transparency/witness-quorum`, and
`/transparency/gossip`. There are no public signing or import routes. Runtime
evidence is atomically retained under ignored `runtime/witnesses/` and
`runtime/gossip/`.

```powershell
.\.venv\Scripts\python.exe scripts\generate_transparency_witness_keys.py
```

Manual exchange uses `export_checkpoint_gossip.py`,
`verify_checkpoint_gossip.py`, and `import_checkpoint_gossip.py`. Missing
consistency evidence is `consistency-unproven`, distinct from a proven split
view.

## Local setup

Create the reference Registry Authority key pair once, or validate the existing
pair without changing it:

```powershell
.\.venv\Scripts\python.exe scripts\generate_registry_authority_keys.py
```

The generator refuses partial or mismatched pairs and never overwrites a valid
existing pair. Key files under `implementation/keys/` are local and ignored by
Git.

Run the demonstrator from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\manage_database.py upgrade
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir implementation
```

Then open `http://127.0.0.1:8000`.

## Python integration

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
gap version
```

Providers use `GapProvider.issue_credential()` and verifiers use
`GapVerifier.verify()`. Full online verification preserves the service's trust,
transparency, witness and gossip policy. Cryptographic-only results are
explicitly labelled and never presented as full verification. See
[`docs/SDK.md`](docs/SDK.md), [`docs/ProviderIntegration.md`](docs/ProviderIntegration.md)
and [`docs/VerifierIntegration.md`](docs/VerifierIntegration.md).

## License

Check LICENSE file

Deployment and operational procedures are in
[`docs/Deployment.md`](docs/Deployment.md),
[`docs/Operations.md`](docs/Operations.md),
[`docs/Administration.md`](docs/Administration.md), and
[`docs/BackupAndRecovery.md`](docs/BackupAndRecovery.md).

## Current limitations

Federation is configuration-based. The reference implementation does not crawl
remote registries, poll authority endpoints, reconcile conflicting decisions,
provide authority quorum or consensus, persist production data, or integrate
with blockchains, certificate transparency, HSMs or cloud key management.
The local private keys are demonstration material rather than a production
key-custody design. There is no public submission, remote gossip, witness
cosigning, multi-log quorum, blockchain anchoring, CT interoperability,
distributed consensus, OAuth, KMS/HSM integration or
automatic rotation. Sprint 13 should add witness cosigning, checkpoint gossip
and split-view monitoring.
