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