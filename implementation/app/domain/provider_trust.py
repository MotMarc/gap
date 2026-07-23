from dataclasses import dataclass
from datetime import datetime
from typing import Literal


ProviderTrustStatus = Literal[
    "self-declared",
    "applicant",
    "approved",
    "suspended",
    "removed",
]


@dataclass(frozen=True, slots=True)
class ProviderTrustDecision:
    """
    Represents one authoritative trust-registry decision for a provider.
    """

    decision_id: str
    provider_id: str
    status: ProviderTrustStatus
    authority: str
    reason: str
    decided_at: datetime

    def __post_init__(self) -> None:
        if not self.decision_id.strip():
            raise ValueError("Trust decision IDs cannot be empty.")

        if not self.provider_id.strip():
            raise ValueError("Trust decision provider IDs cannot be empty.")

        if not self.authority.strip():
            raise ValueError("Trust decision authorities cannot be empty.")

        if not self.reason.strip():
            raise ValueError("Trust decision reasons cannot be empty.")

        if self.decided_at.tzinfo is None:
            raise ValueError("Trust decision timestamps must be timezone-aware.")
