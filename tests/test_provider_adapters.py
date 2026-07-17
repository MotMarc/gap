import sys
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.adapters.demo_image_adapter import DemoImageAdapter  # noqa: E402
from app.services.provider_adapter_repository import (  # noqa: E402
    ProviderAdapterNotFoundError,
    ProviderAdapterRepository,
)


def test_demo_adapter_generates_valid_png() -> None:
    adapter = DemoImageAdapter()

    artifact = adapter.generate("A cryptographically attributable generated image.")

    assert artifact.media_type == "image/png"
    assert artifact.filename.endswith(".png")
    assert artifact.model_id == "gap-demo-image-v1"
    assert len(artifact.content) > 0

    image = Image.open(BytesIO(artifact.content))

    assert image.format == "PNG"
    assert image.size == (1024, 1024)


def test_demo_adapter_rejects_empty_prompt() -> None:
    adapter = DemoImageAdapter()

    with pytest.raises(
        ValueError,
        match="A non-empty prompt is required.",
    ):
        adapter.generate("   ")


def test_adapter_repository_resolves_provider() -> None:
    adapter = DemoImageAdapter()
    repository = ProviderAdapterRepository([adapter])

    assert repository.get("gap-demo-provider") is adapter


def test_adapter_repository_rejects_duplicate_provider() -> None:
    adapter = DemoImageAdapter()
    repository = ProviderAdapterRepository([adapter])

    with pytest.raises(ValueError):
        repository.add(DemoImageAdapter())


def test_unknown_provider_adapter_raises_error() -> None:
    repository = ProviderAdapterRepository()

    with pytest.raises(ProviderAdapterNotFoundError):
        repository.get("unknown-provider")
