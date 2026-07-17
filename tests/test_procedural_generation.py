import sys
from io import BytesIO
from pathlib import Path

from PIL import Image


IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.adapters.demo_image_adapter import DemoImageAdapter  # noqa: E402


def test_same_prompt_produces_identical_artifact() -> None:
    adapter = DemoImageAdapter()

    first_artifact = adapter.generate("A blue geometric city beside an ocean.")

    second_artifact = adapter.generate("A blue geometric city beside an ocean.")

    assert first_artifact.content == second_artifact.content
    assert first_artifact.model_id == "gap-semantic-procedural-image-v2"


def test_different_prompts_produce_different_artifacts() -> None:
    adapter = DemoImageAdapter()

    first_artifact = adapter.generate("A red mechanical landscape at sunset.")

    second_artifact = adapter.generate("A green forest beneath a dark night sky.")

    assert first_artifact.content != second_artifact.content


def test_procedural_artifact_is_valid_png() -> None:
    adapter = DemoImageAdapter()

    artifact = adapter.generate(
        "A purple abstract structure made from layered circles."
    )

    image = Image.open(BytesIO(artifact.content))

    assert image.format == "PNG"
    assert image.mode == "RGB"
    assert image.size == (1024, 1024)
    assert artifact.media_type == "image/png"
    assert artifact.filename == "gap-generated-artifact.png"


def test_prompt_whitespace_is_normalised() -> None:
    adapter = DemoImageAdapter()

    first_artifact = adapter.generate("A yellow geometric composition.")

    second_artifact = adapter.generate("   A yellow geometric composition.   ")

    assert first_artifact.content == second_artifact.content
