import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_DIRECTORY = PROJECT_ROOT / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.core.provider_config import (  # noqa: E402
    KEY_ID,
    PRIVATE_KEY_PATH,
    PROVIDER_ID,
    PROVIDER_NAME,
    PUBLIC_KEY_PATH,
)
from app.crypto.provider_keys import (  # noqa: E402
    load_private_key,
    load_public_key,
)
from app.services.artifact_service import (  # noqa: E402
    create_artifact_descriptor,
)
from app.services.generation_credential_service import (  # noqa: E402
    create_credential_payload,
    issue_generation_credential,
)
from app.services.generation_event_service import (  # noqa: E402
    create_generation_event,
)
from app.services.provider_identity_service import (  # noqa: E402
    create_provider_identity_document,
)
from app.services.verification_service import (  # noqa: E402
    verify_generation_credential,
)


def main() -> None:
    print()
    print("GAP Reference Demonstrator v0.0.1")
    print("=" * 40)

    artifact_bytes = b"A generated artifact protected by GAP"

    print("\nCreating Generation Event...")
    event = create_generation_event(
        provider_id=PROVIDER_ID,
        model_id="demo-model-v1",
    )
    print("OK")

    print("\nHashing artifact...")
    artifact = create_artifact_descriptor(
        artifact=artifact_bytes,
        media_type="text/plain",
    )
    print("OK")

    print("\nCreating Generation Credential Payload...")
    payload = create_credential_payload(
        event=event,
        artifacts=[artifact],
    )
    print("OK")

    print("\nSigning Generation Credential...")
    private_key = load_private_key(PRIVATE_KEY_PATH)

    credential = issue_generation_credential(
        payload=payload,
        key_id=KEY_ID,
        private_key=private_key,
    )
    print("OK")

    print("\nLoading Provider Identity Document...")
    public_key = load_public_key(PUBLIC_KEY_PATH)

    provider_document = create_provider_identity_document(
        provider_id=PROVIDER_ID,
        provider_name=PROVIDER_NAME,
        key_id=KEY_ID,
        public_key=public_key,
    )
    print("OK")

    print("\nVerifying Generation Credential...")
    valid = verify_generation_credential(
        credential=credential,
        provider_document=provider_document,
    )

    print("VALID" if valid else "INVALID")

    print("\nCredential summary")
    print("-" * 40)
    print(f"Provider:      {credential.payload.provider.provider_id}")
    print(f"Generation ID: {credential.payload.generation.generation_id}")
    print(f"Credential ID: {credential.payload.credential_id}")
    print(f"Model:         {credential.payload.model.model_id}")
    print(f"Algorithm:     {credential.proof.type}")
    print(f"Key ID:        {credential.proof.key_id}")
    print(f"Result:        {'VALID' if valid else 'INVALID'}")

    if not valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
