# Protocol test vectors

Sprint 16 cases add normalized PNG binding, package and embedded tampering,
profile confusion, unknown-profile and downgrade refusal while leaving
historical v0.15 objects unchanged.

Vectors under `protocol/test-vectors/v0.15/` use conspicuously labelled,
test-only keys and fixed timestamps and identifiers. The 20-scenario catalogue
covers valid text/binary data, artifact/payload/signature tampering, unknown and
lifecycle keys, provider/authority/federation failures, inclusion and
consistency proofs, witness quorum, split view, equivocation, stale material,
and incomplete cryptographic-only verification. The manifest records SDK
version, vector format, expected result and SHA-256 for each file.

Run `.\.venv\Scripts\python.exe scripts\generate_sdk_test_vectors.py --check`
to detect drift. Never deploy vector keys. They exist only for compatibility
testing of canonical bytes, digest binding, signature verification and
tampering failures.
