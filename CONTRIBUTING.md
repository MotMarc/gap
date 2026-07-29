# Contributing

Use Python 3.10 or newer in a project virtual environment. Install the project
with its `dev` extra, then run Ruff, both vector checks and the complete pytest
suite. Migrations are explicit, ordered and immutable after release. Protocol
changes require threat-model, compatibility, specification, vector and
cross-implementation review; security-sensitive changes require a second
reviewer.

Never commit deployment keys, administrator tokens, `.env` files, databases,
backups, runtime state, private attribution records or browser profiles.
Canonicalisation and cryptographic policy must not be reimplemented in an
integration layer.
