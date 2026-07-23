# Threat Model

## Registry trust boundary

Provider-controlled credentials and identity documents cannot assert provider
approval or local registry-authority trust. Trust decisions are portable only
through signatures over deterministic canonical JSON. Verification resolves
the exact authority ID and exact key ID, rejects unknown or revoked keys, and
requires the signed payload to match the current local decision.

Malformed Base64, invalid Ed25519 public keys and invalid signatures are handled
as verification failures. Public API schemas exclude private key paths and
provider onboarding contact references.

Generation Credentials cannot assert `provider_trusted`,
`registry_authority_trusted` or `trust_attestation_valid`. Provider identity
documents cannot assert those values either. The local trust repository and
signed-attestation verifier are the only sources of registry trust.

Private onboarding contact references are accepted only as private application
input and never returned in public trust responses. Account references, prompts
and raw Provider Attribution Records remain separate from public credentials.
They are retained provider-side and exposed only through the authorised,
audited disclosure workflow.

The reference authority private key is a local demonstration key, not a
production custody design. Authentication, remote federation, persistence,
secure key storage, HSM integration, quorum, transparency logs and compromise
recovery remain out of scope.

Other current limitations include in-memory repositories, configuration-only
federation, no remote authority discovery, no authenticated registry
administration, no transparency log, no consensus or quorum, and no automated
cross-registry conflict resolution.

## Federation bundle threats

Sprint 11 rejects unknown authorities/keys, revoked keys, malformed signatures,
excessive lifetime, expiry, future issuance beyond five minutes, sequence gaps,
replays, rollbacks, missing predecessors, chain mismatches, duplicates,
cross-authority attestations, and invalid contained attestations. Retired keys
may verify history but cannot sign new state. Verification completes before
repository or filesystem mutation.

Imported JSON is size- and count-limited and uses atomic accepted-file writes.
Public APIs expose no paths, private keys, contacts, accounts, prompts, or
attribution records. There is no mutation API or remote fetch. Conflicting valid
authority decisions fail closed; expired signed data remains audit-only.
Production persistence, authenticated administration, secure key custody and
transparency-log proofs remain limitations. Sprint 12 should add signed tree
heads/inclusion proofs or authenticated transport with strict allowlisting.
