import sys
from pathlib import Path

import pytest


IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.domain.provider import Provider  # noqa: E402
from app.services.provider_repository import (  # noqa: E402
    ProviderNotFoundError,
    ProviderRepository,
)


def create_provider(
    provider_id: str = "test-provider",
) -> Provider:
    return Provider(
        provider_id=provider_id,
        provider_name="Test Provider",
        key_id="test-key",
        private_key_path=Path("private.key"),
        public_key_path=Path("public.key"),
    )


def test_provider_can_be_added_and_retrieved() -> None:
    repository = ProviderRepository()

    provider = create_provider()
    repository.add(provider)

    assert repository.get("test-provider") == provider


def test_unknown_provider_raises_error() -> None:
    repository = ProviderRepository()

    with pytest.raises(ProviderNotFoundError):
        repository.get("unknown-provider")


def test_duplicate_provider_is_rejected() -> None:
    provider = create_provider()
    repository = ProviderRepository([provider])

    with pytest.raises(ValueError):
        repository.add(provider)


def test_multiple_providers_can_be_listed() -> None:
    repository = ProviderRepository(
        [
            create_provider("provider-one"),
            create_provider("provider-two"),
        ]
    )

    provider_ids = {provider.provider_id for provider in repository.list_all()}

    assert provider_ids == {
        "provider-one",
        "provider-two",
    }
