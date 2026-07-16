from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ProviderAttributionRecord:
    """
    Confidential provider-side record associated with a Generation Event.

    This record must never be embedded within a public Generation Credential.
    """

    generation_id: str
    provider_id: str
    account_reference: str
    prompt_hash: str
    model_id: str
    created_at: datetime
    retention_status: str
