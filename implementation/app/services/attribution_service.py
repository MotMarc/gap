import hashlib

from app.domain.generation_event import GenerationEvent
from app.domain.provider_attribution_record import ProviderAttributionRecord


def hash_prompt(prompt: str) -> str:
    """
    Hash a prompt using SHA-256.

    The public Generation Credential never contains this value.
    """

    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def create_provider_attribution_record(
    event: GenerationEvent,
    account_reference: str,
    prompt: str,
) -> ProviderAttributionRecord:
    """
    Create a confidential Provider Attribution Record for a Generation Event.
    """

    return ProviderAttributionRecord(
        generation_id=event.generation_id,
        provider_id=event.provider_id,
        account_reference=account_reference,
        prompt_hash=hash_prompt(prompt),
        model_id=event.model_id,
        created_at=event.created_at,
        retention_status="active",
    )
