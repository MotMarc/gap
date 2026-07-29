# Known limitations

The reference deployment has no HSM/KMS integration, automated key rotation,
remote gossip transport, multi-log consensus, authority quorum, OAuth, built-in
production rate limiter, universal media parser, C2PA interoperability,
blockchain anchoring or commercial-provider certification. Local performance
figures are not production capacity claims. Availability and denial-of-service
protection depend on operator infrastructure. A compromised active issuer can
sign false claims until revocation reaches verifiers.
Docker release validation was unavailable on the 2026-07-29 reference machine
because the Docker executable was absent. This remains explicitly blocked; it
has not been treated as a passing check. Advisory-backed vulnerability scanning
and standards-compliant SBOM generation were also unavailable and are not
claimed.
