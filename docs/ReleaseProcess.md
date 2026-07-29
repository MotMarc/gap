# Release process

Run `python scripts/validate_mvp_release.py --full` from an isolated checkout
with the project virtual environment active. Review its JSON report and all
skips.

## v1.0.0 checklist

- [ ] Working tree and complete diff reviewed
- [ ] Version 1.0.0 consistent; protocol and public contracts frozen
- [ ] Historical compatibility, Ruff, tests, warnings and all vectors pass
- [ ] Wheel/sdist build, clean install, package contents and CLI smoke pass
- [ ] Docker/configuration, migrations and persistence restart pass
- [ ] Backup/restore and online/offline/cross-installation equivalence pass
- [ ] Provider, verifier and service conformance pass
- [ ] Browser console/resources and mobile/desktop flows pass
- [ ] No private keys changed; no secrets, runtime files or databases staged
- [ ] Changelog, limitations, security policy and review package complete
- [ ] Buyer demo and final release validator pass
- [ ] Commit reviewed
- [ ] `v1.0.0` tag and release notes created manually

Never let automation commit, push, tag, regenerate deployment keys or delete
operator volumes.

The full validator now runs performance, backup/restore and the buyer demo as
mandatory checks. Unavailable Docker is `blocked` and makes the command fail.
Only the repository owner may explicitly waive that environmental block:

```powershell
python scripts/validate_mvp_release.py --full `
  --owner-approve-unavailable-docker `
  --owner-exception-justification "Validated on named release machine"
```

This cannot waive tests, protocol verification, secrets, keys, persistence or
backup failures.

## Release-readiness matrix (2026-07-29)

| Gate | Status | Evidence / limitation |
|---|---|---|
| Tests, vectors, API snapshot | Passed | pytest; three vector checks; OpenAPI check |
| Clean installation | Passed | `validate_clean_install.py` |
| Online/offline/cross-installation | Passed | `validate_cross_installation.py` |
| Browser | Passed | Three viewports; zero exceptions/resources failures |
| Backup/restore | Passed | `release-output/backup-restore.json` |
| Performance | Passed | `release-output/benchmark.json`; local reference only |
| Buyer demo and conformance | Passed | `release-output/mvp-demo/` |
| Docker | Blocked | Docker executable unavailable; owner action required |
| Dependency review | Passed | `pip check`; documented inventory |
| Vulnerability scan | Unavailable | No advisory-backed scanner installed |
| SBOM | Unavailable | No compliant generator installed |
| Review package | Passed | Manifest verification |
