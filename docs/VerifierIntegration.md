# Verifier integration

Discover and negotiate advanced profiles first. Verification always follows the
signed binding: absent means historical raw bytes, PNG means normalized PNG,
and unknown means failure. Package manifests index integrity but do not prove
origin. Online and exported-material offline FULL verification use one policy.

```python
from gap_sdk import GapVerifier

verifier = GapVerifier.from_service("https://gap.example")
result = verifier.verify(artifact_bytes, credential)
```

Online full verification delegates trust, federation, transparency, witness
and gossip policy to the deployed GAP service and independently checks the
artifact digest. Offline construction uses `from_trust_material()` or
`from_local_files()`. Complete v2 bundles reconstruct public-only in-memory
repositories and run the backend signature, federation, transparency, witness
and gossip verification functions without a database, API or network. Missing
evidence is incomplete; cryptographic-only success is never full validity.

Inspect `result.checks`, `missing_evidence`, constituent booleans and safe
diagnostics. Treat stale bundles, unavailable checks, split views, witness
equivocation, federation conflicts and missing evidence as failures for full
verification.
