# GAP Interoperability Profile v1

Identifier: `gap-interop-v1`.

This profile uses canonical UTF-8 JSON with lexicographically sorted keys and no
insignificant whitespace, SHA-256 artifact digests, credential payload version
`0.0.1` (`gap-credential-v1`), `gap-sidecar-v1`, `gap-package-v1`, and
`gap-public-state-v2`.

Supported artifact bindings are `gap-raw-bytes-v1` and
`gap-png-embedded-v1`. The signed artifact descriptor identifies the binding.
A missing binding on a historical credential means raw bytes. Unknown bindings
fail; callers cannot override the signed binding; negotiation never downgrades.

Service capabilities are published at `/.well-known/gap.json`. Discovery is
unsigned capability metadata and is not a trust root. Implementations require
explicit overlap for profile, credential schema, digest, binding, trust format,
and verification level. FULL is never silently reduced.

Limits are 256 KiB per credential or embedded credential, 100 MiB per package,
64 MiB per archive member, 32 archive members, and a 200:1 compression ratio.
Unknown required fields, unsupported compression/media/profile claims, malformed
UTF-8, and contradictory declarations fail closed. Extension fields must be
namespaced and must not change the meaning of defined fields.

PNG binding uses the private ancillary safe-to-copy `gaPc` chunk immediately
before `IEND`. Its data is canonical credential JSON without compression. The
binding digest is SHA-256 over the original PNG bytes with only the single
`gaPc` chunk removed. All other bytes, metadata, chunks, and ordering remain
covered. CRCs and structural bounds are checked; duplicates, truncation,
trailing bytes, invalid ordering, and replacement without explicit consent fail.

Packages are deterministic ZIP archives with fixed ZIP timestamps. The required
members are `manifest.json`, one `artifact/*`, and
`credential/credential.gap.json`; `trust/trust-material.json` is optional.
The manifest indexes sizes and SHA-256 hashes but is not proof of origin.
Credential signatures and signed public trust evidence remain authoritative.
