from datetime import datetime, timezone

from app.crypto.disclosure_id import generate_disclosure_id
from app.domain.disclosure_audit_record import DisclosureAuditRecord
from app.domain.disclosure_authorisation import DisclosureAuthorisation
from app.domain.provider_attribution_record import ProviderAttributionRecord
from app.services.attribution_repository import (
    AttributionRecordNotFoundError,
    AttributionRepository,
)
from app.services.disclosure_audit_repository import DisclosureAuditRepository


SUPPORTED_DISCLOSURE_PURPOSES = {
    "criminal-investigation",
    "civil-proceedings",
    "regulatory-investigation",
    "national-security-investigation",
}


class DisclosureDeniedError(PermissionError):
    """
    Raised when a disclosure request fails authorisation checks.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _utc_now() -> datetime:
    """
    Return the current timezone-aware UTC datetime.
    """

    return datetime.now(timezone.utc)


def _normalise_datetime(value: datetime) -> datetime:
    """
    Ensure a datetime is timezone-aware and represented in UTC.

    Naive datetimes are rejected because their timezone cannot be determined
    reliably.
    """

    if value.tzinfo is None:
        raise DisclosureDeniedError(
            "Authorisation timestamps must include timezone information."
        )

    return value.astimezone(timezone.utc)


def _create_audit_record(
    generation_id: str,
    provider_id: str,
    authorisation: DisclosureAuthorisation,
    approved: bool,
    denial_reason: str | None,
) -> DisclosureAuditRecord:
    """
    Create an immutable audit record for one disclosure attempt.
    """

    return DisclosureAuditRecord(
        disclosure_id=generate_disclosure_id(),
        generation_id=generation_id,
        provider_id=provider_id,
        investigator_reference=authorisation.investigator_reference,
        authorisation_id=authorisation.authorisation_id,
        issuing_authority=authorisation.issuing_authority,
        jurisdiction=authorisation.jurisdiction,
        purpose=authorisation.purpose,
        approved=approved,
        denial_reason=denial_reason,
        disclosed_at=_utc_now(),
    )


def _record_denial(
    generation_id: str,
    provider_id: str,
    authorisation: DisclosureAuthorisation,
    reason: str,
    audit_repository: DisclosureAuditRepository,
) -> None:
    """
    Record a denied disclosure attempt and raise DisclosureDeniedError.
    """

    audit_repository.append(
        _create_audit_record(
            generation_id=generation_id,
            provider_id=provider_id,
            authorisation=authorisation,
            approved=False,
            denial_reason=reason,
        )
    )

    raise DisclosureDeniedError(reason)


def _validate_authorisation(
    record: ProviderAttributionRecord,
    authorisation: DisclosureAuthorisation,
    audit_repository: DisclosureAuditRepository,
) -> None:
    """
    Validate the structural, temporal, and provider-scoping properties of a
    disclosure authorisation.

    This reference implementation does not verify whether the authorisation
    represents a genuine court order or warrant.
    """

    if not authorisation.authorisation_id.strip():
        _record_denial(
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            authorisation=authorisation,
            reason="An authorisation identifier is required.",
            audit_repository=audit_repository,
        )

    if not authorisation.investigator_reference.strip():
        _record_denial(
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            authorisation=authorisation,
            reason="An investigator reference is required.",
            audit_repository=audit_repository,
        )

    if not authorisation.issuing_authority.strip():
        _record_denial(
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            authorisation=authorisation,
            reason="An issuing authority is required.",
            audit_repository=audit_repository,
        )

    if not authorisation.jurisdiction.strip():
        _record_denial(
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            authorisation=authorisation,
            reason="A jurisdiction is required.",
            audit_repository=audit_repository,
        )

    if authorisation.provider_id != record.provider_id:
        _record_denial(
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            authorisation=authorisation,
            reason="The authorisation does not apply to this provider.",
            audit_repository=audit_repository,
        )

    if authorisation.purpose not in SUPPORTED_DISCLOSURE_PURPOSES:
        _record_denial(
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            authorisation=authorisation,
            reason="The disclosure purpose is not supported.",
            audit_repository=audit_repository,
        )

    try:
        issued_at = _normalise_datetime(authorisation.issued_at)
        expires_at = _normalise_datetime(authorisation.expires_at)
    except DisclosureDeniedError as error:
        _record_denial(
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            authorisation=authorisation,
            reason=error.reason,
            audit_repository=audit_repository,
        )

    current_time = _utc_now()

    if expires_at <= issued_at:
        _record_denial(
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            authorisation=authorisation,
            reason="The authorisation expiry must be after its issue time.",
            audit_repository=audit_repository,
        )

    if issued_at > current_time:
        _record_denial(
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            authorisation=authorisation,
            reason="The authorisation is not yet valid.",
            audit_repository=audit_repository,
        )

    if expires_at <= current_time:
        _record_denial(
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            authorisation=authorisation,
            reason="The authorisation has expired.",
            audit_repository=audit_repository,
        )


def disclose_attribution_record(
    generation_id: str,
    authorisation: DisclosureAuthorisation,
    attribution_repository: AttributionRepository,
    audit_repository: DisclosureAuditRepository,
) -> ProviderAttributionRecord:
    """
    Resolve a Generation Identifier to its private Provider Attribution Record.

    Every successful or denied authorisation attempt is written to the
    disclosure audit repository.

    Requests for unknown Generation Identifiers raise
    AttributionRecordNotFoundError. They are not added to the provider's
    disclosure log because no associated provider record exists.
    """

    try:
        record = attribution_repository.get(generation_id)
    except AttributionRecordNotFoundError:
        raise

    _validate_authorisation(
        record=record,
        authorisation=authorisation,
        audit_repository=audit_repository,
    )

    audit_repository.append(
        _create_audit_record(
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            authorisation=authorisation,
            approved=True,
            denial_reason=None,
        )
    )

    return record
