# Threat Model

## Sprint 14 operational threats

Database compromise exposes persistent application state and private
onboarding/attribution data, though never signing keys. Database integrity
constraints, signed-object verification, Merkle recomputation and
persistent-state audits detect classes of corruption but do not prevent an
attacker with database access from deleting or rolling back all evidence.
External checkpoints and protected backups remain necessary.

Migrations are explicit and revision-checked; this detects an absent or stale
revision, not maliciously modified migration code. Backups use SHA-256
manifests to detect accidental or unauthorised modification but are not
encrypted or signed by default. Theft exposes their database contents.
Restores require explicit confirmation and post-restore audit, but an authentic
old backup can still cause rollback.

Administrator token theft permits pilot administrative transitions. The
service stores only its hash, uses constant-time comparison, accepts it only in
the bearer header and records a fingerprint/request ID audit event. HTTPS,
network restriction and external secret rotation remain deployment duties;
there is no replay nonce, OAuth or role system.

Structured logging escapes line breaks and redacts named secret fields, but
novel sensitive fields or dependency logs remain a residual leakage risk.
Request-size limits reduce simple denial of service but are not a complete
rate-limiting platform. Production rejects wildcard CORS.

Container operation is non-root and keys are read-only mounts. Container
escape, weak host volume permissions, an exposed PostgreSQL port, stale base
images and host compromise remain external risks. Compose keeps the database
on an internal network but is not a hardened HA platform.

## Witness and gossip threats

A signed checkpoint can be shown selectively. GAP therefore requires fresh
statements from locally trusted independent witnesses and consistent gossip.
Unknown witnesses/keys, revoked keys and stale evidence never count toward
current quorum. One witness cannot count twice, and the log operator cannot
witness itself.

Contradictory evidence is retained instead of resolving by majority, timestamp
or arrival order. Same-size different-root checkpoints fail as a split view; a
witness signature on both is equivocation; tree-size regression is rollback.
Invalid consistency fails, while absent proof is separately reported as
consistency unproven. Packages are bounded, public-only and atomically
persisted. There is no remote fetching, polling or unauthenticated import.

## Transparency threats

An entry's local existence is not proof of inclusion, and an unsigned root is
not authoritative. Verification therefore requires a typed entry with a
recomputed object digest, a structurally valid Merkle audit path, a signed tree
head, the exact trusted log identity/key, and known-consistent checkpoint state.
Retired keys preserve historical verification; unknown and revoked keys fail.

Inclusion proves membership but does not validate the underlying attestation or
bundle. Consistency proves append-only extension but does not prevent an
operator from presenting separate views without gossip. Same log and tree size
with different roots is reported as `split-view-detected` and fails closed.

Runtime objects are bounded, parsed as typed schemas, written atomically and
never expose paths. Invalid startup objects are excluded and counted. Public
entries cannot contain private onboarding contacts, accounts, prompts,
attribution/disclosure records, generated artifacts, private keys or raw
credentials.

The reference implementation has no remote gossip, witness cosigning,
multi-log quorum, blockchain anchoring, CT interoperability, production
database, distributed consensus, OAuth, KMS/HSM support or automatic key
rotation. Witness cosigning, checkpoint gossip and split-view monitoring are
the recommended Sprint 13 direction.

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
