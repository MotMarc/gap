# Generation Attribution Protocol v1.0

This document specifies the v1 reference profile; it has no standards-body
approval.

## Roles and objects

A Provider owns a Provider Identity and signing-key history. A Registry
Authority signs provider trust decisions. A Transparency Log Operator appends
typed public evidence and signs tree heads. Independent Witnesses sign exact
checkpoints. A Verifier applies locally configured trust and freshness policy.

A Generation Credential MUST contain its schema version, collision-resistant
credential and generation identifiers, provider/key identifiers, issuance
timestamp, generation context, and one or more ArtifactDescriptors. Each
descriptor MUST bind media type, SHA-256 digest and binding-profile identifier.
The provider signature MUST cover the complete canonical payload.

## Canonicalisation and signatures

Objects MUST serialize as UTF-8 JSON with keys lexically sorted, no insignificant
whitespace, direct Unicode, JSON booleans/null/integers and no floating-point
values. Optional absent fields are omitted. Signatures use Ed25519 over those
exact bytes. Base64, public keys and signatures MUST be strictly decoded and
length checked. Unknown algorithms MUST fail.

## Trust and transparency

Provider keys MUST be evaluated at issuance time. Revoked keys MUST fail;
retired keys MAY verify valid history. Trust decisions MUST be append-only and
signed by an accepted Registry Authority. Federation sequences MUST increase
and bind their predecessor; rollback or conflict MUST fail closed.

Leaves use `SHA256(0x00 || canonical_entry)` and nodes use
`SHA256(0x01 || left || right)`. Tree heads MUST bind log identity, size, root
and timestamp. Inclusion and consistency proofs MUST be verified against an
accepted signed head. Witness statements MUST bind the exact checkpoint.
Split views, rollback, insufficient quorum and witness equivocation MUST fail
FULL verification.

## Artifact profiles

`gap-artifact-sha256-v1` binds raw bytes and MAY be carried in the v1 sidecar.
`gap-png-normalized-sha256-v1` hashes a valid PNG after removing its single GAP
ancillary chunk. Portable `gap-package-v1` archives MUST index and hash every
member, reject traversal, links, duplicates, excessive expansion and unsupported
compression. Manifest integrity MUST NOT replace credential authenticity.

## Verification

Requested FULL verification MUST validate artifact integrity, credential
signature, provider lifecycle and trust, authority attestation, federation,
transparency, witness quorum, gossip consistency and freshness. A skipped or
unavailable check MUST NOT count as passed, and FULL MUST NOT silently
downgrade. Offline trust material MUST contain public evidence only and obey the
same policy. Discovery MAY negotiate supported capabilities but MUST NOT serve
as a trust root.

## Compatibility, privacy and security

Verifiers SHOULD retain declared v0.15/v0.16 compatibility. Unknown profiles
and unsupported major versions MUST fail closed. Private attribution records,
administrator tokens and private keys MUST NOT be public protocol data.
Operators MUST provide TLS, rate limiting, secure key custody, monitoring,
backup protection and prompt revocation. GAP cannot prove truth after an
authorized signing system is compromised and does not provide anonymity,
legal certification, universal media coverage or C2PA compliance.
