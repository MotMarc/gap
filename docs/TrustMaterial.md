# Public trust material

The `gap-public-state-v2` envelope contains a manifest and public state:
providers, registry authorities, trust decisions and attestations, federation
bundles, transparency entries and signed tree heads, witness statements,
public log/witness identities, proofs, quorum policy and gossip observations.
Its SHA-256 covers deterministic canonical JSON for
`state`. It must never contain contacts, prompts, tokens, database URLs, paths,
private keys, backups or private attribution records.

`load_trust_material()` validates the manifest before returning data.
Applications should impose an age limit on `exported_at`, distribute bundles
over authenticated channels, and preserve the prior valid cache if refresh
fails. Atomic replacement prevents partial local writes. A digest detects
corruption, not a malicious publisher or proof of origin; signed objects are
still verified. `TrustMaterialCache` is opt-in, bounded and expiring.
