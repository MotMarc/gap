import sys
from datetime import datetime, timezone
from pathlib import Path

IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.crypto.provider_keys import generate_provider_key_pair  # noqa: E402
from app.domain.generation_event import GenerationEvent  # noqa: E402
from app.services.artifact_service import (  # noqa: E402
    create_artifact_descriptor,
)
from app.services.generation_credential_service import (  # noqa: E402
    create_credential_payload,
    issue_generation_credential,
)
from app.services.verification_service import (  # noqa: E402
    verify_generation_credential,
)


def create_test_event() -> GenerationEvent:
    return GenerationEvent(
        generation_id="gid_" + "a" * 64,
        provider_id="gap-demo-provider",
        model_id="demo-model-v1",
        created_at=datetime.now(timezone.utc),
        gap_version="0.1",
    )


def test_generation_credential_signature_is_valid() -> None:
    private_key, public_key = generate_provider_key_pair()

    artifact = create_artifact_descriptor(
        artifact=b"generated artifact",
        media_type="text/plain",
    )

    payload = create_credential_payload(
        event=create_test_event(),
        artifacts=[artifact],
    )

    credential = issue_generation_credential(
        payload=payload,
        key_id="key-2026-01",
        private_key=private_key,
    )

    assert credential.proof.type == "Ed25519"
    assert credential.proof.key_id == "key-2026-01"

    assert verify_generation_credential(
        credential=credential,
        public_key=public_key,
    )


def test_modified_payload_fails_verification() -> None:
    private_key, public_key = generate_provider_key_pair()

    artifact = create_artifact_descriptor(
        artifact=b"original artifact",
        media_type="text/plain",
    )

    payload = create_credential_payload(
        event=create_test_event(),
        artifacts=[artifact],
    )

    credential = issue_generation_credential(
        payload=payload,
        key_id="key-2026-01",
        private_key=private_key,
    )

    credential.payload.model.model_id = "tampered-model"

    assert not verify_generation_credential(
        credential=credential,
        public_key=public_key,
    )


def test_different_public_key_fails_verification() -> None:
    private_key, _ = generate_provider_key_pair()
    _, incorrect_public_key = generate_provider_key_pair()

    artifact = create_artifact_descriptor(
        artifact=b"generated artifact",
        media_type="text/plain",
    )

    payload = create_credential_payload(
        event=create_test_event(),
        artifacts=[artifact],
    )

    credential = issue_generation_credential(
        payload=payload,
        key_id="key-2026-01",
        private_key=private_key,
    )

    assert not verify_generation_credential(
        credential=credential,
        public_key=incorrect_public_key,
    )


def test_modified_signature_fails_verification() -> None:
    private_key, public_key = generate_provider_key_pair()

    artifact = create_artifact_descriptor(
        artifact=b"generated artifact",
        media_type="text/plain",
    )

    payload = create_credential_payload(
        event=create_test_event(),
        artifacts=[artifact],
    )

    credential = issue_generation_credential(
        payload=payload,
        key_id="key-2026-01",
        private_key=private_key,
    )

    credential.proof.signature = "A" + credential.proof.signature[1:]

    assert not verify_generation_credential(
        credential=credential,
        public_key=public_key,
    )
