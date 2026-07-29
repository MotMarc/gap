# Provider integration

Publish a Provider Identity Document and keep its active Ed25519 private key
outside the application repository. GAP does not generate a key during normal
issuance.

```python
from gap_sdk import GapProvider

provider = GapProvider.from_key_file(
    provider_identity=identity,
    private_key_path="provider-private.key",
)
credential = provider.issue_credential(
    artifact=artifact_bytes,
    generation_context={
        "model": "model-v1",
        "request_id": "public-request-reference",
        "media_type": "image/png",
    },
)
provider.save_credential("artifact.png", credential)
```

The sidecar is `artifact.png.gap.json`, UTF-8 deterministic JSON with
`gap-sidecar-v1` and the complete public credential. It contains no path or
private key and refuses overwrite unless explicitly requested. Files are
SHA-256 hashed in chunks. Supply media type explicitly; filenames are not a
trusted content-type source.

`CredentialSigner` has only `key_id` and `sign(payload)` and can later be
implemented by KMS/HSM or remote custody. `provider-doctor` checks identity,
active-key selection, and key-pair consistency without printing key material.
Python memory cannot guarantee private-key zeroisation.
