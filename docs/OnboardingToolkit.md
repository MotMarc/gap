# Onboarding toolkit

`gap-provider-onboarding-v1` declares public identity keys, capabilities,
profiles and a test credential. Its manifest excludes private keys and
production contact data. Submission uses the existing application API and
never automatically approves a provider; backend transitions remain authoritative.

1. Create and protect a provider key using the existing development setup or
   production custody process.
2. Submit the public identity through the authenticated administrative
   onboarding workflow.
3. Run `gap provider doctor --identity identity.json --private-key key.file`.
4. Issue a test sidecar with `gap credential issue`.
5. Verify at cryptographic level, then against a deployed service at full
   level.
6. Retain test evidence and document key rotation and incident contacts.

CLI exits are: 0 success, 1 general, 2 usage, 3 malformed input, 4 artifact
mismatch, 5 cryptographic failure, 6 provider/federation trust, 7
transparency, 8 witness/gossip/split view, 9 network/service, and 10 incomplete
or stale FULL verification. JSON output does not change status.

Commands are `version`, `credential issue`, `credential inspect`, `verify`,
`trust export`, `trust inspect`, `diagnostics`, and `provider doctor`.
`GapAdministrativeClient` alone carries a bearer token and exposes authorised
trust transitions and audit queries; it never uploads a key or auto-approves.
