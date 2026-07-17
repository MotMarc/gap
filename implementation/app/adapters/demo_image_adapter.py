from io import BytesIO

from app.domain.generated_artifact import GeneratedArtifact
from app.procedural.renderer import ProceduralRenderer


MODEL_ID = "gap-semantic-procedural-image-v2"


class DemoImageAdapter:
    """
    Generate deterministic, prompt-responsive procedural PNG artifacts.

    This adapter is CPU-only and does not use a generative AI model.
    It exists to demonstrate GAP generation, credential issuance and
    verification without requiring external services or specialist hardware.
    """

    def __init__(self) -> None:
        self._renderer = ProceduralRenderer()

    @property
    def provider_id(self) -> str:
        return "gap-demo-provider"

    def generate(self, prompt: str) -> GeneratedArtifact:
        image = self._renderer.render(prompt)

        output = BytesIO()

        image.save(
            output,
            format="PNG",
            optimize=False,
        )

        return GeneratedArtifact(
            content=output.getvalue(),
            media_type="image/png",
            filename="gap-generated-artifact.png",
            model_id=MODEL_ID,
        )
