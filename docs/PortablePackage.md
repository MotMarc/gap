# Portable Package

`.gapbundle` is `gap-package-v1`, a deterministic ZIP container. Its manifest
indexes every non-manifest member by exact size and SHA-256 digest. That index
detects damage but does not authenticate origin; GAP credentials and signed
trust evidence do.

Readers reject traversal, absolute/drive/backslash paths, NUL names,
case-insensitive duplicates, links, unsupported compression, excessive members,
oversized members/archives, and compression ratios over 200:1. Verification
works in memory. Extraction requires an explicit destination, checks integrity
first, refuses overwrite by default, and uses atomic file replacement.
