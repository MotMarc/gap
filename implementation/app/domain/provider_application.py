from dataclasses import dataclass
from datetime import datetime
from typing import Literal


ProviderApplicationStatus = Literal[
    "submitted",
    "approved",
    "rejected",
    "withdrawn",
]


@dataclass(frozen=True, slots=True)
class ProviderOnboardingApplication:
    """
    Represents a provider's private onboarding application.
    """

    application_id: str
    provider_id: str
    provider_name: str
    contact_reference: str
    submitted_at: datetime
    status: ProviderApplicationStatus = "submitted"

    def __post_init__(self) -> None:
        if not self.application_id.strip():
            raise ValueError("Provider application IDs cannot be empty.")

        if not self.provider_id.strip():
            raise ValueError("Provider application provider IDs cannot be empty.")

        if not self.provider_name.strip():
            raise ValueError("Provider application names cannot be empty.")

        if not self.contact_reference.strip():
            raise ValueError("Provider application contact references cannot be empty.")

        if self.submitted_at.tzinfo is None:
            raise ValueError("Provider application timestamps must be timezone-aware.")

    @property
    def is_active(self) -> bool:
        return self.status == "submitted"
