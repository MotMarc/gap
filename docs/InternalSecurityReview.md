# Internal security review

This is a maintainer-performed adversarial review, not an independent audit.

| Component | Attack surface / threat | Existing mitigation and evidence | Residual risk | v1 action |
|---|---|---|---|---|
| Canonicalisation and Ed25519 | ambiguous bytes, key substitution | one UTF-8 canonicaliser; exact public-key and algorithm validation; signing tests | no formal proof | reject floats; golden tests |
| Key lifecycle | stolen or stale signing key | issuance-time status, retirement history, revocation failure | compromise before revocation | operator response documented |
| Registry/federation | forged trust, rollback, conflict | signed attestations, sequence/hash chain, fail-closed conflict tests | trusted authority compromise | retain audit evidence |
| Transparency | omitted/reordered history | immutable leaf order, signed heads, inclusion/consistency tests | single-log availability | post-MVP multi-log study |
| Witness/gossip | split view/equivocation | exact checkpoint binding, quorum, retained conflicts | manual exchange | document operational cadence |
| Offline/cache | stale or injected material | signed evidence, digest, freshness, atomic cache; FULL fails closed | delayed refresh | explicit diagnostics |
| Sidecar/package/PNG | traversal, bombs, duplicate metadata | member/count/size/ratio limits, symlink rejection, CRC and chunk bounds | resource exhaustion below limits | proxy request limits |
| HTTP provider | SSRF, redirects, oversized response | configured endpoint, bounded response and safe errors | operator can configure hostile endpoint | restrict deployment config |
| Public/admin API | unauthorized mutation, token leakage | bearer header only, constant-time comparison, audit records, safe errors | brute-force traffic | reverse-proxy rate limiting |
| Persistence/backup | partial writes, rollback, corrupt history | transactions, explicit migrations, integrity audit, manifest verification | storage administrator compromise | rehearse isolated restore |
| Docker/frontend/CLI | secret inclusion, XSS, traceback/path leakage | non-root image, dockerignore, text rendering, stable errors | TLS/host hardening external | package and browser audits |

Critical finding fixed: repository tests could inherit operator persistence
settings and touch retained evidence. Test configuration now unconditionally
selects isolated memory persistence. No protocol policy was weakened.
