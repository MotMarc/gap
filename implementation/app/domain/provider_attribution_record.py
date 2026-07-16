from dataclasses import dataclass
from datetime import datetime
from typing import Literal


RetentionStatus = Literal[
    "active",
    "expired",
    "deleted",
]


@dataclass(frozen=True, slots=True)
class ProviderAttributionRecord:
    """
    Confidential provider-side record associated with a Generation Event.

    Provider Attribution Records are never embedded within public Generation
    Credentials. They exist exclusively within provider-controlled systems.
    """

    generation_id: str
    provider_id: str
    account_reference: str
    prompt_hash: str
    model_id: str
    created_at: datetime
    retained_until: datetime
    retention_status: RetentionStatus
