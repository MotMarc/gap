# Security policy

## Supported versions

Security fixes are provided for the latest 1.0.x release. Older experimental
versions receive no routine fixes, although their protocol objects remain
verification-compatible where documented.

## Reporting a vulnerability

Open a minimal repository issue asking the owner for a private reporting
channel; do not include exploit details or secrets in the public issue. The
repository owner must replace this process with a dedicated private contact
before public release. Include affected versions, impact, prerequisites,
reproduction steps and suggested mitigations. Please allow acknowledgement and
coordinated remediation before publishing an unpatched vulnerability.

Compromised provider, registry, log or witness keys must be revoked through the
authoritative lifecycle and replaced without deleting history. A compromised
administrator token must be rotated immediately, its audit trail reviewed, and
affected state integrity checked from a known checkpoint and backup.
