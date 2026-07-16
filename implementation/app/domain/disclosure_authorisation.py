from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DisclosureAuthorisation:
    """
    Represents the legal or administrative authority presented when requesting
    disclosure of a private Provider Attribution Record.

    The reference implementation validates only structural and temporal
    properties. It does not validate real court orders or government warrants.
    """

    authorisation_id: str
    investigator_reference: str
    issuing_authority: str
    jurisdiction: str
    purpose: str
    issued_at: datetime
    expires_at: datetime
    provider_id: str
