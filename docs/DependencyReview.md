# Dependency review

Runtime dependencies are deliberately small: cryptography supplies Ed25519 and
SHA-256 primitives; httpx supplies bounded HTTP integration; Pydantic validates
SDK models. The service deployment additionally uses FastAPI, Starlette,
SQLAlchemy, Uvicorn, Pillow, pydantic-settings and PostgreSQL's psycopg driver.
Development uses pytest, Ruff and build tooling.

The release environment's `pip check` reported no broken requirements.
Dependencies are pinned in deployment requirements and bounded by compatible
ranges in package metadata. Licence obligations remain those of each upstream
package; GAP's proprietary source-available licence is unchanged.

No vulnerability-database scanner or standards-compliant SBOM generator is
installed, so no vulnerability-scan or SBOM pass is claimed. The deterministic
requirements files are an inventory, not an SPDX or CycloneDX SBOM. External
review should run a current advisory-backed scanner and verify hashes in a
controlled build environment.
