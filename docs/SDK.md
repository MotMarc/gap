# Python SDK

Version 0.16 adds `GapServiceClient.discover()` and `.negotiate()`,
`GapPackage`, PNG helpers, typed HTTP generation adapters, onboarding helpers,
and deterministic conformance reports. Advanced operations require exact
capability overlap and never reduce requested FULL verification.

Install from the repository with `python -m pip install -e .`. The stable
imports are `GapProvider`, `GapVerifier`, `GapServiceClient`,
`GapAdministrativeClient`, `GapCredential`, `VerificationResult`,
`VerificationLevel` and `GapError`.

The SDK supports Python 3.10 and follows the application release version.
Protocol-object versions remain independent. Minor releases may add optional
fields and checks; removals or semantic changes require a major SDK release.
Catch `GapError` for safe operational messages.

```python
from gap_sdk import GapVerifier, VerificationLevel

verifier = GapVerifier.from_service("https://gap.example")
result = verifier.verify(data, credential, level=VerificationLevel.FULL)
if not result.valid:
    print(result.failure_code)
```

Levels are `cryptographic`, `trusted-provider`, and `full`. The requested and
achieved levels are always returned. Skipped or unavailable evidence is never
passed. HTTP clients enable certificate verification, timeouts, response-size
limits, request IDs accepted through normal headers, and an SDK user agent.
Only the administrative client accepts an administrator token; its repr
redacts it and non-local use requires HTTPS. Export with `gap trust export`,
inspect with `gap trust inspect`, and verify offline with `gap verify`. Stale
material may support cryptography but cannot achieve FULL. No browser SDK
exists in this release.
