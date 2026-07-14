from datetime import datetime, timezone

from app.crypto.generation_id import generate_generation_id
from app.domain.generation_event import GenerationEvent

CURRENT_GAP_VERSION = "0.1"


def create_generation_event(
    provider_id: str,
    model_id: str,
) -> GenerationEvent:
    return GenerationEvent(
        generation_id=generate_generation_id(),
        provider_id=provider_id,
        model_id=model_id,
        created_at=datetime.now(timezone.utc),
        gap_version=CURRENT_GAP_VERSION,
    )
