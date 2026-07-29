# Performance

Release measurements must be generated on the review machine and recorded with
Python version, OS, CPU, database mode, sample size and p50/p95/max latency.
Required scenarios are issuance, cryptographic verification, online/offline
FULL verification, package creation/verification, PNG embedding/verification,
trust export/import, transparency growth and service startup.

No hardware-independent latency threshold is asserted. CI checks bounded
completion and output size; these local measurements are not claims of
production-scale throughput or denial-of-service resistance.

## 2026-07-29 reference measurement

Command: `python scripts/benchmark_mvp.py --json --output
release-output/benchmark.json`.

Environment: Windows 10 build 26200, CPython 3.10.0, Intel Family 6 Model 183.
Three repetitions were used. Median SHA-256 time was 0.000403 seconds for 1 MiB
and 0.010120 seconds for 25 MiB. Median issuance time was 0.000565 seconds for
1 MiB and 0.010401 seconds for 25 MiB. Median PNG embedding/extraction times
were 0.001733/0.000863 seconds. Median package creation and integrity checking
for the small fixture were 0.000246/0.000333 seconds. The live buyer demo,
including process isolation and three-way FULL verification, completed in
approximately 4.45 seconds.

These are local reference measurements, not production-capacity guarantees.
No universal throughput claim, distributed load, multi-region deployment or
external-network performance validation occurred.
