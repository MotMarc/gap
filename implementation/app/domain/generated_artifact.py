from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeneratedArtifact:
    """
    Represents an artifact returned by a provider generation adapter.

    The artifact bytes are passed into the GAP credential workflow but are not
    stored inside the Generation Credential itself.
    """

    content: bytes
    media_type: str
    filename: str
    model_id: str
