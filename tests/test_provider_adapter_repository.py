import sys
from pathlib import Path

import pytest


IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.adapters.configurable_svg_adapter import (  # noqa: E402
    ConfigurableSvgAdapter,
)
from app.services.provider_adapter_repository import (  # noqa: E402
    ProviderAdapterNotFoundError,
    ProviderAdapterRepository,
)


def create_adapter(
    provider_id: str = "test-provider",
) -> ConfigurableSvgAdapter:
    return ConfigurableSvgAdapter(
        provider_id=provider_id,
        provider_name="Test Provider",
        model_id="test-model-v1",
        primary_colour="#000000",
        secondary_colour="#ffffff",
        visual_style="Test generation profile",
    )


def test_adapter_can_be_registered_and_retrieved() -> None:
    adapter = create_adapter()
    repository = ProviderAdapterRepository()

    repository.add(adapter)

    assert repository.get("test-provider") == adapter


def test_unknown_adapter_raises_error() -> None:
    repository = ProviderAdapterRepository()

    with pytest.raises(ProviderAdapterNotFoundError):
        repository.get("unknown-provider")


def test_duplicate_adapter_is_rejected() -> None:
    adapter = create_adapter()
    repository = ProviderAdapterRepository([adapter])

    with pytest.raises(ValueError):
        repository.add(adapter)


def test_multiple_provider_adapters_can_be_listed() -> None:
    repository = ProviderAdapterRepository(
        [
            create_adapter("provider-one"),
            create_adapter("provider-two"),
        ],
    )

    assert set(repository.list_provider_ids()) == {
        "provider-one",
        "provider-two",
    }


def test_configurable_adapter_generates_svg() -> None:
    adapter = create_adapter()

    artifact = adapter.generate(
        "A geometric research artifact.",
    )

    assert artifact.media_type == "image/svg+xml"
    assert artifact.filename.endswith(".svg")
    assert artifact.model_id == "test-model-v1"
    assert b"<svg" in artifact.content
    assert b"Test Provider" in artifact.content


def test_same_prompt_produces_same_svg() -> None:
    adapter = create_adapter()

    first = adapter.generate("A deterministic artifact.")
    second = adapter.generate("A deterministic artifact.")

    assert first.content == second.content
    assert first.filename == second.filename


def test_empty_prompt_is_rejected() -> None:
    adapter = create_adapter()

    with pytest.raises(ValueError):
        adapter.generate("   ")
