from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DisclosureAuditRecord:
    """
    Immutable record describing the outcome of one disclosure request.

    Every disclosure attempt is recorded, regardless of whether it is
    approved or denied.
    """

    disclosure_id: str

    generation_id: str

    provider_id: str

    investigator_reference: str

    authorisation_id: str

    issuing_authority: str

    jurisdiction: str

    purpose: str

    approved: bool

    denial_reason: str | None

    disclosed_at: datetime
