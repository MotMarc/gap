import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.domain.generation_event import GenerationEvent  # noqa: E402
from app.services.attribution_repository import (  # noqa: E402
    AttributionRecordAlreadyExistsError,
    AttributionRecordNotFoundError,
    AttributionRepository,
)
from app.services.attribution_service import (  # noqa: E402
    create_provider_attribution_record,
    hash_prompt,
)


def create_test_event() -> GenerationEvent:
    return GenerationEvent(
        generation_id="gid_" + "a" * 64,
        provider_id="gap-demo-provider",
        model_id="demo-model-v1",
        created_at=datetime.now(timezone.utc),
        gap_version="0.1",
    )


def test_prompt_hash_is_deterministic() -> None:
    assert hash_prompt("test prompt") == hash_prompt("test prompt")


def test_prompt_hash_changes_when_prompt_changes() -> None:
    assert hash_prompt("first prompt") != hash_prompt("second prompt")


def test_attribution_record_contains_private_reference() -> None:
    record = create_provider_attribution_record(
        event=create_test_event(),
        account_reference="user-001",
        prompt="Generate an artifact.",
    )

    assert record.account_reference == "user-001"
    assert len(record.prompt_hash) == 64
    assert record.retention_status == "active"


def test_attribution_record_can_be_stored_and_retrieved() -> None:
    repository = AttributionRepository()

    record = create_provider_attribution_record(
        event=create_test_event(),
        account_reference="user-001",
        prompt="Generate an artifact.",
    )

    repository.add(record)

    assert repository.get(record.generation_id) == record


def test_duplicate_attribution_record_is_rejected() -> None:
    repository = AttributionRepository()

    record = create_provider_attribution_record(
        event=create_test_event(),
        account_reference="user-001",
        prompt="Generate an artifact.",
    )

    repository.add(record)

    with pytest.raises(AttributionRecordAlreadyExistsError):
        repository.add(record)


def test_unknown_attribution_record_raises_error() -> None:
    repository = AttributionRepository()

    with pytest.raises(AttributionRecordNotFoundError):
        repository.get("gid_" + "f" * 64)
