import sys
from datetime import datetime, timezone
from pathlib import Path

IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.crypto.canonical_json import canonicalise_model  # noqa: E402
from app.crypto.credential_id import (  # noqa: E402
    generate_credential_id,
    is_valid_credential_id,
)
from app.domain.generation_event import GenerationEvent  # noqa: E402
from app.services.artifact_service import (  # noqa: E402
    create_artifact_descriptor,
)
from app.services.generation_credential_service import (  # noqa: E402
    create_credential_payload,
)


def test_credential_id_is_valid() -> None:
    credential_id = generate_credential_id()

    assert is_valid_credential_id(credential_id)


def test_artifact_descriptor_contains_correct_hash() -> None:
    artifact = create_artifact_descriptor(
        artifact=b"hello GAP",
        media_type="text/plain",
    )

    assert artifact.media_type == "text/plain"
    assert artifact.digest.algorithm == "sha-256"
    assert len(artifact.digest.value) == 64


def test_create_credential_payload() -> None:
    event = GenerationEvent(
        generation_id="gid_" + "a" * 64,
        provider_id="gap-demo-provider",
        model_id="demo-model-v1",
        created_at=datetime.now(timezone.utc),
        gap_version="0.1",
    )

    artifact = create_artifact_descriptor(
        artifact=b"generated artifact",
        media_type="text/plain",
    )

    credential = create_credential_payload(
        event=event,
        artifacts=[artifact],
    )

    assert credential.version == "0.0.1"
    assert credential.generation.generation_id == event.generation_id
    assert credential.provider.provider_id == "gap-demo-provider"
    assert credential.model.model_id == "demo-model-v1"
    assert len(credential.artifacts) == 1
    assert is_valid_credential_id(credential.credential_id)


def test_canonicalisation_is_deterministic() -> None:
    event = GenerationEvent(
        generation_id="gid_" + "b" * 64,
        provider_id="gap-demo-provider",
        model_id="demo-model-v1",
        created_at=datetime(
            2026,
            7,
            14,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        gap_version="0.1",
    )

    artifact = create_artifact_descriptor(
        artifact=b"generated artifact",
        media_type="text/plain",
    )

    credential = create_credential_payload(
        event=event,
        artifacts=[artifact],
    )

    first_result = canonicalise_model(credential)
    second_result = canonicalise_model(credential)

    assert first_result == second_result
    assert isinstance(first_result, bytes)
