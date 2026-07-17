from typing import Protocol

from app.domain.generated_artifact import GeneratedArtifact


class ProviderGenerationAdapter(Protocol):
    """
    Interface implemented by systems capable of producing generated artifacts.

    GAP does not define how generation occurs. It requires only that a provider
    adapter returns artifact bytes, a media type, a filename, and a model
    identifier.
    """

    @property
    def provider_id(self) -> str:
        """
        Return the stable GAP provider identifier represented by this adapter.
        """

    def generate(self, prompt: str) -> GeneratedArtifact:
        """
        Produce one generated artifact from a prompt.
        """
