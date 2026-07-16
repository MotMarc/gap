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
    Raised when a disclosure request fails provider policy checks.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalise_datetime(value: datetime) -> datetime:
    """
    Return a timezone-aware UTC datetime.

    Naive datetimes are rejected because their intended timezone cannot be
    reliably established.
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


def _validate_record_lifecycle(
    record: ProviderAttributionRecord,
    authorisation: DisclosureAuthorisation,
    attribution_repository: AttributionRepository,
    audit_repository: DisclosureAuditRepository,
) -> ProviderAttributionRecord:
    """
    Ensure that the Provider Attribution Record remains available for lawful
    disclosure.
    """

    if record.retention_status == "deleted":
        _record_denial(
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            authorisation=authorisation,
            reason="The attribution record has been deleted.",
            audit_repository=audit_repository,
        )

    if record.retention_status == "expired":
        _record_denial(
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            authorisation=authorisation,
            reason="The attribution record has expired.",
            audit_repository=audit_repository,
        )

    if record.retained_until <= _utc_now():
        expired_record = attribution_repository.set_retention_status(
            generation_id=record.generation_id,
            retention_status="expired",
        )

        _record_denial(
            generation_id=expired_record.generation_id,
            provider_id=expired_record.provider_id,
            authorisation=authorisation,
            reason="The attribution record has expired.",
            audit_repository=audit_repository,
        )

    return record


def _validate_authorisation(
    record: ProviderAttributionRecord,
    authorisation: DisclosureAuthorisation,
    audit_repository: DisclosureAuditRepository,
) -> None:
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
    Resolve a Generation Identifier to a private Provider Attribution Record.

    Every authorised or denied attempt relating to an existing attribution
    record is written to the disclosure audit log.
    """

    try:
        record = attribution_repository.get(generation_id)
    except AttributionRecordNotFoundError:
        raise

    record = _validate_record_lifecycle(
        record=record,
        authorisation=authorisation,
        attribution_repository=attribution_repository,
        audit_repository=audit_repository,
    )

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
