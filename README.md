# Generation Attribution Protocol (GAP)

GAP is an open protocol proposal for privacy-preserving attribution of AI-generated artefacts.

The objective of GAP is to enable participating AI providers to cryptographically associate generated artefacts with a unique Generation Identifier while preserving user privacy by default and supporting lawful attribution under due process.

## Current Status

Early research and reference implementation, version 0.10.0.

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
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir implementation
```

Then open `http://127.0.0.1:8000`.

## License

MIT

## Sprint 10 limitations

Federation is configuration-based. The reference implementation does not crawl
remote registries, poll authority endpoints, reconcile conflicting decisions,
provide authority quorum or consensus, persist production data, or integrate
with blockchains, certificate transparency, HSMs or cloud key management.
The local authority private key is demonstration material rather than a
production key-custody design. The browser tests include static and API-backed
coverage; a reusable browser automation suite is not yet part of the repository.
