# External Provider Pilot

`examples/external_provider_service.py` is an independent deterministic PNG
service, not a commercial AI vendor. Run it separately and connect with
`HttpGenerationProviderAdapter`. GAP signing keys and administrator tokens are
never sent to it. Prompts are not logged by the adapter.

The adapter requires HTTPS except for loopback development, verifies TLS by
default, refuses redirects, bounds responses, validates declared media types,
redacts authorization in representations, and blocks explicit private/link-local
IP targets unless deliberately allowed.

The cross-installation harness launches this provider as a third process,
generates the PNG through HTTP, and compares Instance A online FULL,
disconnected SDK FULL and Instance B portable FULL results field by field.
