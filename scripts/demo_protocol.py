import base64
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_DIRECTORY = PROJECT_ROOT / "implementation"
OUTPUT_DIRECTORY = PROJECT_ROOT / "demo-output"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.main import app  # noqa: E402


def main() -> None:
    client = TestClient(app)

    print()
    print("GAP Reference Demonstrator v0.0.1")
    print("=" * 50)

    print("\nGenerating an artifact through the demo provider...")

    generation_response = client.post(
        "/generations/create",
        json={
            "provider_id": "gap-demo-provider",
            "account_reference": "demo-user-001",
            "prompt": (
                "A generated artifact demonstrating privacy-preserving attribution."
            ),
            "retention_days": 365,
        },
    )

    if generation_response.status_code != 201:
        print(generation_response.text)
        raise SystemExit(1)

    generation_result = generation_response.json()
    credential = generation_result["credential"]

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    artifact_path = OUTPUT_DIRECTORY / generation_result["filename"]
    credential_path = OUTPUT_DIRECTORY / "generation-credential.json"

    artifact_path.write_bytes(
        base64.b64decode(
            generation_result["artifact_base64"],
            validate=True,
        )
    )

    credential_path.write_text(
        json.dumps(
            credential,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Artifact generated.")
    print(f"Artifact written to:   {artifact_path}")
    print(f"Credential written to: {credential_path}")

    print("\nVerifying the Generation Credential...")

    verification_response = client.post(
        "/credentials/verify",
        json={
            "credential": credential,
        },
    )

    verification_result = verification_response.json()

    print("Credential VALID" if verification_result["valid"] else "Credential INVALID")

    print("\nCredential summary")
    print("-" * 50)
    print(f"Provider:      {verification_result['provider_id']}")
    print(f"Generation ID: {verification_result['generation_id']}")
    print(f"Credential ID: {verification_result['credential_id']}")
    print(f"Algorithm:     {verification_result['algorithm']}")
    print(f"Key ID:        {verification_result['key_id']}")

    if not verification_result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
