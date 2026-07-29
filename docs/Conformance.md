# Conformance

Conformance reports use `gap-conformance-report-v1`. Cases are sorted before
canonical hashing. A required failure or skip fails the suite; optional skips
remain visible. Reports contain normalized public results rather than secrets.
The report SHA-256 detects tampering but is not a third-party certification.

Provider suites cover discovery, generation, media/size limits, and safe error
behavior. Verifier suites cover raw and PNG profiles, packages, FULL online and
offline results, tampering, and downgrade refusal. Service suites cover public
discovery, issuance, trust export, restart stability, and cross-instance use.

Live acceptance commands:

```powershell
.\.venv\Scripts\python.exe scripts\validate_browser_console.py --url http://127.0.0.1:8780 --launch-service --json
.\.venv\Scripts\python.exe scripts\validate_cross_installation.py --json
```

Browser failures are classified from CDP Runtime, Log and Network events.
Uncaught exceptions, promise rejections and failed required resources fail the
run. A favicon or source map is optional only when its exact URL is identified;
the reference frontend supplies a local favicon.
