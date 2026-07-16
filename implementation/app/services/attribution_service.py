import hashlib
from datetime import timedelta

from app.domain.generation_event import GenerationEvent
from app.domain.provider_attribution_record import ProviderAttributionRecord


DEFAULT_RETENTION_DAYS = 365
MAXIMUM_RETENTION_DAYS = 3650


def hash_prompt(prompt: str) -> str:
    """
    Hash a generation prompt using SHA-256.

    The public Generation Credential never contains the prompt or its hash.
    The prompt hash is retained privately to support provider-side
    investigation and record integrity checks.
    """

    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def create_provider_attribution_record(
    event: GenerationEvent,
    account_reference: str,
    prompt: str,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> ProviderAttributionRecord:
    """
    Create a confidential Provider Attribution Record.

    The retention period is measured from the Generation Event timestamp.
    """

    if not account_reference.strip():
        raise ValueError("An account reference is required.")

    if not prompt.strip():
        raise ValueError("A prompt is required.")

    if retention_days < 1:
        raise ValueError("The attribution retention period must be at least one day.")

    if retention_days > MAXIMUM_RETENTION_DAYS:
        raise ValueError("The attribution retention period cannot exceed 3650 days.")

    return ProviderAttributionRecord(
        generation_id=event.generation_id,
        provider_id=event.provider_id,
        account_reference=account_reference,
        prompt_hash=hash_prompt(prompt),
        model_id=event.model_id,
        created_at=event.created_at,
        retained_until=event.created_at + timedelta(days=retention_days),
        retention_status="active",
    )
