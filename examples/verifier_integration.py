from pathlib import Path

from gap_sdk import GapVerifier
from gap_sdk.models import GapCredential


artifact = Path("artifact.bin").read_bytes()
credential = GapCredential.model_validate_json(
    Path("credential.json").read_text("utf-8")
)
result = GapVerifier.from_service("http://127.0.0.1:8000").verify(artifact, credential)
print(result.summary)
