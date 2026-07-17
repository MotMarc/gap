import hashlib
import textwrap
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from app.domain.generated_artifact import GeneratedArtifact


IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 1024
BACKGROUND_COLOUR = (242, 242, 242)
TEXT_COLOUR = (30, 30, 30)
ACCENT_COLOUR = (70, 70, 70)


class DemoImageAdapter:
    """
    Lightweight provider adapter that creates a deterministic PNG image.

    This adapter demonstrates the GAP provider integration workflow without
    requiring a large local model or an external generation API.
    """

    @property
    def provider_id(self) -> str:
        return "gap-demo-provider"

    def generate(self, prompt: str) -> GeneratedArtifact:
        cleaned_prompt = prompt.strip()

        if not cleaned_prompt:
            raise ValueError("A non-empty prompt is required.")

        image = Image.new(
            mode="RGB",
            size=(IMAGE_WIDTH, IMAGE_HEIGHT),
            color=BACKGROUND_COLOUR,
        )

        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        prompt_digest = hashlib.sha256(cleaned_prompt.encode("utf-8")).hexdigest()

        draw.rectangle(
            xy=(60, 60, IMAGE_WIDTH - 60, IMAGE_HEIGHT - 60),
            outline=ACCENT_COLOUR,
            width=4,
        )

        draw.text(
            xy=(100, 110),
            text="GAP Demo Provider",
            fill=TEXT_COLOUR,
            font=font,
        )

        draw.text(
            xy=(100, 150),
            text="Generated Artifact",
            fill=TEXT_COLOUR,
            font=font,
        )

        wrapped_prompt = textwrap.wrap(
            cleaned_prompt,
            width=65,
        )

        vertical_position = 240

        for line in wrapped_prompt[:15]:
            draw.text(
                xy=(100, vertical_position),
                text=line,
                fill=TEXT_COLOUR,
                font=font,
            )
            vertical_position += 28

        draw.text(
            xy=(100, IMAGE_HEIGHT - 160),
            text=f"Prompt digest: {prompt_digest[:32]}",
            fill=ACCENT_COLOUR,
            font=font,
        )

        draw.text(
            xy=(100, IMAGE_HEIGHT - 120),
            text="Model: gap-demo-image-v1",
            fill=ACCENT_COLOUR,
            font=font,
        )

        output = BytesIO()

        image.save(
            output,
            format="PNG",
            optimize=True,
        )

        return GeneratedArtifact(
            content=output.getvalue(),
            media_type="image/png",
            filename="gap-generated-artifact.png",
            model_id="gap-demo-image-v1",
        )
