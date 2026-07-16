from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DisclosureAuditRecord:
    """
    Records one controlled disclosure of a Provider Attribution Record.
    """

    disclosure_id: str
    generation_id: str
    provider_id: str
    investigator_reference: str
    authorisation_reference: str
    disclosed_at: datetime
