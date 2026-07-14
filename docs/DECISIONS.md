# Decision 001

## Title

Generation Identifiers are opaque.

## Status

Accepted

## Date

14 July 2026

## Decision

Generation Identifiers (GIDs) SHALL be cryptographically random and SHALL NOT encode user identities, prompts, timestamps, provider identities, or any other metadata.

## Rationale

Embedding metadata within a GID introduces privacy risks, enables unwanted correlation between generation events, and complicates future protocol evolution.

Instead, all contextual information is stored separately within the Provider Attribution Record (PAR).

The GID functions solely as the immutable identity of a Generation Event.

# Decision 002

## Title

Progressive Attribution

## Status

Accepted

## Date

14 July 2026

## Decision

GAP adopts Progressive Attribution instead of Universal Attribution.

## Rationale

Universal attribution is technically infeasible because offline models, modified implementations, and non-participating providers will continue to exist.

Instead, every provider implementing GAP increases the proportion of AI-generated artefacts that can be cryptographically attributed.

The protocol therefore delivers measurable value even under partial adoption.

# Decision 003

## Title

Open Protocol

## Status

Accepted

## Date

14 July 2026

## Decision

GAP SHALL be published as an open protocol rather than proprietary technology.

## Rationale

The protocol should encourage interoperability between providers instead of vendor lock-in.

Multiple independent reference implementations should be possible.

# Decision 004

## Title

Privacy by Default

## Status

Accepted

## Date

14 July 2026

## Decision

Public verification SHALL never reveal user identity.

Identity resolution SHALL only occur through provider-controlled attribution records under existing legal processes.

# Decision 005

## Title

Generation Events are protocol primitives.

## Status

Accepted

## Date

14 July 2026

## Decision

GAP authenticates Generation Events rather than generated artefacts themselves.

## Rationale

Generated media may be modified, transformed, compressed, or reformatted.

Generation Events remain immutable and therefore provide a stable foundation for cryptographic attribution.

# Decision 006

## Title

Ed25519 provider signing keys

## Status

Accepted

## Date

14 July 2026

## Decision

GAP reference providers SHALL use Ed25519 key pairs to sign Generation
Credentials during the experimental protocol phase.

Each provider SHALL protect its private signing key and publish the
corresponding public key through a Provider Identity Document.

## Rationale

Ed25519 provides compact keys and signatures, deterministic signing, strong
security properties, and broad implementation support.

The choice remains provisional until the protocol undergoes formal
cryptographic review.

# Decision 007

## Title

GAP is artifact-agnostic

## Status

Accepted

## Date

14 July 2026

## Decision

The Generation Attribution Protocol SHALL apply to generated artifacts
independently of the underlying generative system or output modality.

GAP SHALL NOT be limited to AI-generated images or media.

A Generation Event MAY produce one or more artifacts, including but not limited
to images, video, audio, text, source code, documents, three-dimensional assets,
synthetic datasets, or other machine-generated outputs.

## Rationale

Restricting GAP to contemporary AI image generation would unnecessarily couple
the protocol to a specific technology and output type.

The protocol's fundamental purpose is to establish cryptographically verifiable
attribution for generation events. The underlying model, system, and artifact
format are implementation details belonging to the provider.

An artifact-agnostic design allows GAP to remain applicable as generative
technologies evolve.

## Consequences

Generation Credentials SHALL represent associated outputs through an
`artifacts` collection rather than a single image-specific field.

Each artifact entry SHALL include a media type and a cryptographic digest.

The protocol SHALL avoid terminology and fields that assume a specific output
modality.

# Decision 008

## Title

Generation Credentials use deterministic canonical JSON

## Status

Accepted provisionally

## Date

14 July 2026

## Decision

The experimental GAP reference implementation SHALL serialize unsigned
Generation Credential payloads as compact JSON with alphabetically sorted
object keys, direct Unicode representation, and UTF-8 encoding before signing.

The `signature` field SHALL NOT be included within the signed payload.

## Rationale

Digital signatures operate over bytes. Different whitespace, key ordering, or
character escaping can cause logically equivalent JSON objects to produce
different byte sequences.

A deterministic representation is therefore necessary for repeatable signing
and verification.

## Limitations

The current mechanism is suitable for the experimental Python reference
implementation but is not yet considered a final cross-language
canonicalisation standard.

Future versions SHALL evaluate adoption of the JSON Canonicalization Scheme
defined by RFC 8785.

# Decision 010

## Title

Provider Identity Documents publish verification keys

## Status

Accepted

## Date

14 July 2026

## Decision

Participating providers SHALL publish a Provider Identity Document containing
their provider identifier and one or more public verification keys.

Each public key SHALL include a key identifier, algorithm, encoded public key
value, and operational status.

Generation Credentials SHALL reference the signing key through the `key_id`
field in their proof object.

## Rationale

Publishing multiple verification keys enables key rotation while preserving the
verifiability of previously issued credentials.

The Provider Identity Document separates public cryptographic identity from
private provider infrastructure and avoids requiring a central verification
service.

# Decision 009

## Title

Generation Credentials separate payloads from cryptographic proofs

## Status

Accepted

## Date

14 July 2026

## Decision

A Generation Credential SHALL consist of exactly one Generation Credential
Payload and exactly one cryptographic proof.

The proof SHALL contain the signature algorithm, signing key identifier, and
encoded signature value.

The proof SHALL NOT be included in the canonical bytes signed by the provider.

## Rationale

Separating the signed payload from its cryptographic proof prevents ambiguity
regarding the data covered by the signature.

This design also permits future cryptographic algorithms to be introduced
without changing the structure of the Generation Credential Payload.

The provider, rather than GAP itself, issues and signs each Generation
Credential.

# Decision 010

## Title

Provider Identity Documents publish verification keys

## Status

Accepted

## Date

14 July 2026

## Decision

Each participating provider SHALL publish a Provider Identity Document
containing its stable provider identifier and one or more public verification
keys.

Each verification key SHALL define a key identifier, signature algorithm,
encoded public-key value, and operational status.

A Generation Credential SHALL identify its signing key through the `key_id`
field in its proof object.

## Rationale

A Provider Identity Document allows independent verifiers to obtain the public
key required to authenticate a Generation Credential.

Publishing multiple keys supports key rotation while preserving the ability to
verify credentials issued under older keys.

This design avoids requiring a central GAP verification service.

## Key statuses

An active key MAY be used for new credentials and verification.

A retired key MUST NOT be used to issue new credentials but MAY remain valid
for verifying historical credentials.

A revoked key MUST NOT be trusted for credential verification.