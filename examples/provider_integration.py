import json
from pathlib import Path

from gap_sdk import GapProvider
from gap_sdk.models import ProviderIdentity


identity = ProviderIdentity.model_validate_json(
    Path("provider-identity.json").read_text("utf-8")
)
provider = GapProvider.from_key_file(identity, "provider-private.key")
artifact = b"example generated artifact\n"
credential = provider.issue_credential(
    artifact,
    {"model": "example-model-v1", "media_type": "text/plain"},
)
print(json.dumps(credential.model_dump(mode="json"), indent=2))
