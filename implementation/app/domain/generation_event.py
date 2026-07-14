from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class GenerationEvent:
    """
    Represents one GAP-compatible AI generation event.

    This object records the identity of the generation event. It does not
    contain the generated artifact, prompt, user identity, or private
    attribution information.
    """

    generation_id: str
    provider_id: str
    model_id: str
    created_at: datetime
    gap_version: str
