# GAP Reference Architecture

## Signed registry trust

Sprint 10 separates four independently visible checks:

1. Generation Credential cryptographic validity.
2. Provider trust status.
3. Signed trust-attestation validity.
4. Local trust in the registry authority.

The final browser result is:

```text
overall_valid =
    artifact_integrity_valid
    AND credential_cryptographic_valid
    AND provider_trusted
    AND trust_attestation_valid
    AND registry_authority_trusted
```

`POST /credentials/verify` does not receive artifact bytes, so it reports the
credential and signed-registry controls. The browser independently calculates
artifact integrity and combines it with the API result.

Provider identity documents remain authoritative only for provider signing-key
ownership. Registry-authority identity documents publish a separate Ed25519 key
history. Active authority keys sign new attestations, retired keys preserve
historical verification, and revoked keys invalidate referenced attestations.
Unsigned decisions and unknown authorities cannot establish production trust.

Repositories are append-only in-memory stores. Federation means configuring
multiple locally accepted authorities; it does not perform remote discovery or
synchronization.

## Components and boundaries

### Registry Authority identity

`RegistryAuthority` owns a stable authority ID, display name, active key ID and
complete signing-key history. Its public identity document is built separately
from provider identities. Authority IDs and key IDs are exact values; an
attestation cannot select an arbitrary public key.

Authority keys have three lifecycle states:

- `active`: signs new attestations and verifies existing attestations;
- `retired`: cannot sign new attestations but verifies historical attestations;
- `revoked`: rejects every referenced attestation.

### Signed trust-decision attestations

The attestation payload contains the decision, provider, status, decision
authority, reason, decision timestamp, Registry Authority identity,
attestation ID and issuance time. The complete canonical payload is signed
using Ed25519. Any payload change invalidates the signature.

Verification resolves the exact locally configured authority and exact
published key, rejects revoked keys before signature acceptance, and requires
the attestation payload to match the current provider trust decision.

### Configuration-based federation

`RegistryAuthorityRepository` is the local trusted-authority configuration.
More than one authority can be registered, but Sprint 10 performs no network
fetching or automatic reconciliation. A correctly signed attestation from an
authority absent from this repository remains untrusted.

### Issuance policy

New Generation Credentials require:

1. a provider whose current status is `approved`;
2. a current matching signed trust attestation;
3. a valid attestation signature from a locally trusted authority;
4. an active provider signing key with available private key material.

Provider identity alone, an unsigned decision or a provider-controlled
credential field cannot satisfy registry trust.

## Public routes

- `GET /registry-authorities`
- `GET /registry-authorities/{authority_id}/.well-known/gap-registry.json`
- `GET /trust-attestations`
- `GET /trust-attestations/{attestation_id}`
- `GET /trust-registry`
- `GET /providers/{provider_id}/trust`
- `POST /credentials/verify`

## Local authority keys

The reference authority pair is generated or validated with:

```powershell
.\.venv\Scripts\python.exe scripts\generate_registry_authority_keys.py
```

The generator is idempotent, rejects partial and mismatched pairs, and leaves a
valid existing pair unchanged. The application does not generate keys during
startup.
