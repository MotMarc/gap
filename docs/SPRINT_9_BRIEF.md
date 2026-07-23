# Sprint 9 — Provider Onboarding and Trust Registry

## Current baseline

The current GAP application version is 0.8.0.

The complete test suite currently passes with 89 tests.

Completed capabilities include:

- FastAPI reference implementation
- browser demonstrator
- Generation Credentials
- SHA-256 artifact binding
- Ed25519 credential signing
- credential canonicalisation
- independent provider identity documents
- three provider-specific generation adapters
- exact provider and key resolution
- provider substitution detection
- active, retired and revoked signing keys
- Private Attribution Records
- controlled disclosure
- disclosure audit logging

Current providers:

- `gap-demo-provider` — GAP Demo Provider
- `aurora-ai` — Aurora AI
- `meridian-ai` — Meridian AI

## Sprint goal

Introduce a governed trust layer that is separate from provider-controlled
cryptographic identity.

A Provider Identity Document proves which keys belong to a provider.

It must not allow a provider to declare itself trusted or approved.

Trust must be resolved independently through a GAP Trust Registry.

## Core architectural principle

Cryptographic authenticity and ecosystem trust are separate decisions.

A credential can be cryptographically authentic while still being issued by
a provider that is not currently trusted.

Verification must therefore report both:

1. Whether the credential is cryptographically valid.
2. Whether the issuing provider is currently trusted by the GAP registry.

## Required provider trust statuses

Implement these statuses:

- `self-declared`
- `applicant`
- `approved`
- `suspended`
- `removed`

Only `approved` providers are trusted ecosystem participants.

### Status meaning

#### self-declared

The provider has a cryptographic identity but has not submitted a formal
onboarding application.

#### applicant

The provider has submitted an onboarding application but has not been
approved.

#### approved

The provider is an admitted GAP ecosystem participant.

Its active signing key may issue new credentials, and cryptographically valid
credentials may receive an overall valid verification result.

#### suspended

The provider is temporarily not trusted.

Existing credentials may still be cryptographically authentic, but their
overall GAP verification result must not be valid while the provider is
suspended.

A suspended provider must not issue new credentials.

#### removed

The provider has been permanently removed from the trusted ecosystem.

Its credentials may remain cryptographically authentic for forensic purposes,
but their overall GAP verification result must not be valid.

A removed provider must not issue new credentials.

## Required status transitions

Support and validate these transitions:

- `self-declared` → `applicant`
- `applicant` → `approved`
- `applicant` → `removed`
- `approved` → `suspended`
- `approved` → `removed`
- `suspended` → `approved`
- `suspended` → `removed`

`removed` is terminal.

Invalid transitions must raise a domain or service error.

## Trust decision records

Trust changes must be represented as explicit decision records.

Each decision should contain at least:

- `decision_id`
- `provider_id`
- `status`
- `authority`
- `reason`
- `decided_at`

The registry should preserve decision history rather than overwriting the
previous record silently.

The provider's current trust status is derived from its latest valid decision.

## Provider onboarding applications

Add an onboarding application model and repository.

An application should contain at least:

- `application_id`
- `provider_id`
- `provider_name`
- `contact_reference`
- `submitted_at`
- `status`

Submitting an application moves a self-declared provider into the applicant
state.

The contact reference is private onboarding information.

It must not be exposed through public trust-registry responses.

Duplicate active applications should be rejected.

Already-approved providers should not be able to submit another active
application.

## Trust registry

Add an in-memory trust registry following the repository and service patterns
already used in GAP.

Seed the three existing providers as approved:

- `gap-demo-provider`
- `aurora-ai`
- `meridian-ai`

The registry must be independent of:

- Provider Identity Documents
- provider signing keys
- provider generation adapters
- Generation Credential payloads

A provider must not be able to change its trust status by modifying its
identity document or credential.

## Public API

Implement suitable Pydantic request and response models.

Add these public endpoints, or equivalent routes that match the repository's
existing conventions:

### List registry participants

`GET /trust-registry`

Return public trust summaries.

Do not expose private application contact references.

### Read provider trust

`GET /providers/{provider_id}/trust`

Return:

- provider ID
- current trust status
- whether the provider is trusted
- latest decision metadata
- public decision history where appropriate

### Submit onboarding application

`POST /provider-applications`

Create an applicant record.

The response may expose the generated application ID and public submission
status, but must not echo private information unnecessarily.

## Administrative decisions

Do not add unauthenticated public endpoints that approve, suspend or remove
providers.

For Sprint 9, trust decisions may be:

- configured during application startup
- performed through internal services
- exercised through automated tests

A later milestone can add authenticated registry-authority administration.

## Credential issuance policy

Only an approved provider may issue a new GAP credential through the
reference implementation.

Credential issuance must fail clearly for providers with these statuses:

- self-declared
- applicant
- suspended
- removed

Do not weaken the existing active-key requirement.

A provider must be both:

- approved by the trust registry
- using its active signing key

before issuing a new credential.

## Credential verification policy

Preserve all current cryptographic verification controls:

- exact provider ID resolution
- exact key ID resolution
- Ed25519 signature verification
- rejected revoked keys
- accepted retired historical keys
- rejected unknown keys
- separate artifact SHA-256 verification

Extend the verification response with clear trust information.

Include fields equivalent to:

- `valid`
- `cryptographic_valid`
- `provider_trusted`
- `provider_trust_status`
- `trust_decision_id`
- existing provider, generation, credential, key and algorithm fields

The exact naming may follow existing schema conventions.

### Overall validity

The overall result must follow:

`valid = cryptographic_valid AND provider_trusted`

Only the `approved` status sets `provider_trusted` to true.

### Suspended or removed providers

A correctly signed historical credential from a suspended or removed provider
should report:

- `cryptographic_valid = true`
- `provider_trusted = false`
- `valid = false`

This distinction is important for forensic and historical analysis.

## Provider identity documents

Do not make the provider's own identity document authoritative for trust.

The identity document should continue describing:

- provider identity
- verification keys
- key algorithms
- key lifecycle statuses

Trust status must come from the independent registry.

## Provider listing

Extend provider discovery responses with trust information where appropriate.

The frontend must still dynamically discover participating providers.

Do not make an applicant provider selectable for generation unless it has an
approved trust state and a registered generation adapter.

## Browser demonstrator

Update the browser demonstrator to display:

- provider trust status
- an approved, applicant, suspended or removed badge style
- the independent trust-registry source
- trust decision information
- cryptographic validity separately from ecosystem trust
- an additional verification timeline stage for registry trust resolution

The verification result must clearly distinguish between:

- fully valid and trusted
- cryptographically authentic but untrusted
- cryptographically invalid

Add a public Trust Registry section or panel showing the current ecosystem
participants and their status.

Do not add unauthenticated administrative controls to the browser.

## Required tests

Add tests covering at least:

1. Existing providers are seeded as approved.
2. Approved providers may issue credentials.
3. Applicant providers may not issue credentials.
4. Suspended providers may not issue credentials.
5. Removed providers may not issue credentials.
6. A valid credential from an approved provider is fully valid.
7. A cryptographically valid credential from a suspended provider reports
   cryptographic validity but fails overall verification.
8. A cryptographically valid credential from a removed provider reports
   cryptographic validity but fails overall verification.
9. Self-declared providers are not trusted.
10. Applicant providers are not trusted.
11. Invalid trust-status transitions fail.
12. Removed status is terminal.
13. Trust decision history is retained.
14. A provider cannot self-assert approval through its identity document.
15. A provider cannot self-assert approval through a credential payload.
16. Private onboarding contact information is absent from public registry
    responses.
17. Duplicate active applications are rejected.
18. Existing key-lifecycle behaviour remains unchanged.
19. Existing provider-substitution behaviour remains unchanged.
20. Browser trust-registry elements are served correctly.

Update older tests only when the Sprint 9 behaviour deliberately changes
their expected response.

## Version

Update the application and demonstrator version to:

`0.9.0`

Avoid duplicated hard-coded version values where practical.

## Quality requirements

Run:

```powershell
python -m ruff format implementation tests scripts
python -m ruff check implementation tests scripts
python -m pytest -v