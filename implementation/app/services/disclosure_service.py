from datetime import datetime, timezone

from app.crypto.disclosure_id import generate_disclosure_id
from app.domain.disclosure_audit_record import DisclosureAuditRecord
from app.domain.provider_attribution_record import ProviderAttributionRecord
from app.services.attribution_repository import AttributionRepository
from app.services.disclosure_audit_repository import DisclosureAuditRepository


def disclose_attribution_record(
    generation_id: str,
    investigator_reference: str,
    authorisation_reference: str,
    attribution_repository: AttributionRepository,
    audit_repository: DisclosureAuditRepository,
) -> ProviderAttributionRecord:
    """
    Resolve a Generation Identifier to its private attribution record.

    The MVP treats a non-empty authorisation reference as simulated lawful
    authority. Real legal validation is outside the current implementation.
    """

    if not investigator_reference.strip():
        raise ValueError("An investigator reference is required.")

    if not authorisation_reference.strip():
        raise ValueError("An authorisation reference is required.")

    record = attribution_repository.get(generation_id)

    audit_repository.append(
        DisclosureAuditRecord(
            disclosure_id=generate_disclosure_id(),
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            investigator_reference=investigator_reference,
            authorisation_reference=authorisation_reference,
            disclosed_at=datetime.now(timezone.utc),
        )
    )

    return record
