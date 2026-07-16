import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.domain.disclosure_authorisation import (  # noqa: E402
    DisclosureAuthorisation,
)
from app.domain.generation_event import GenerationEvent  # noqa: E402
from app.services.attribution_repository import (  # noqa: E402
    AttributionRepository,
)
from app.services.attribution_service import (  # noqa: E402
    create_provider_attribution_record,
)
from app.services.disclosure_audit_repository import (  # noqa: E402
    DisclosureAuditRepository,
)
from app.services.disclosure_service import (  # noqa: E402
    DisclosureDeniedError,
    disclose_attribution_record,
)


def create_test_event() -> GenerationEvent:
    return GenerationEvent(
        generation_id="gid_" + "a" * 64,
        provider_id="gap-demo-provider",
        model_id="demo-model-v1",
        created_at=datetime.now(timezone.utc),
        gap_version="0.1",
    )


def create_valid_authorisation(
    provider_id: str = "gap-demo-provider",
    purpose: str = "criminal-investigation",
) -> DisclosureAuthorisation:
    current_time = datetime.now(timezone.utc)

    return DisclosureAuthorisation(
        authorisation_id="court-order-001",
        investigator_reference="investigator-001",
        issuing_authority="Crown Court",
        jurisdiction="GB",
        purpose=purpose,
        issued_at=current_time - timedelta(minutes=5),
        expires_at=current_time + timedelta(hours=1),
        provider_id=provider_id,
    )


def create_repositories() -> tuple[
    AttributionRepository,
    DisclosureAuditRepository,
]:
    attribution_repository = AttributionRepository()
    audit_repository = DisclosureAuditRepository()

    record = create_provider_attribution_record(
        event=create_test_event(),
        account_reference="user-001",
        prompt="Generate an artifact.",
    )

    attribution_repository.add(record)

    return attribution_repository, audit_repository


def test_valid_authorisation_discloses_record() -> None:
    attribution_repository, audit_repository = create_repositories()

    record = disclose_attribution_record(
        generation_id="gid_" + "a" * 64,
        authorisation=create_valid_authorisation(),
        attribution_repository=attribution_repository,
        audit_repository=audit_repository,
    )

    assert record.account_reference == "user-001"
    assert audit_repository.count() == 1
    assert audit_repository.list_all()[0].approved is True


def test_expired_authorisation_is_denied() -> None:
    attribution_repository, audit_repository = create_repositories()

    current_time = datetime.now(timezone.utc)

    authorisation = DisclosureAuthorisation(
        authorisation_id="court-order-expired",
        investigator_reference="investigator-001",
        issuing_authority="Crown Court",
        jurisdiction="GB",
        purpose="criminal-investigation",
        issued_at=current_time - timedelta(hours=2),
        expires_at=current_time - timedelta(hours=1),
        provider_id="gap-demo-provider",
    )

    with pytest.raises(
        DisclosureDeniedError,
        match="The authorisation has expired.",
    ):
        disclose_attribution_record(
            generation_id="gid_" + "a" * 64,
            authorisation=authorisation,
            attribution_repository=attribution_repository,
            audit_repository=audit_repository,
        )

    assert audit_repository.count() == 1

    audit_record = audit_repository.list_all()[0]

    assert audit_record.approved is False
    assert audit_record.denial_reason == "The authorisation has expired."


def test_future_authorisation_is_denied() -> None:
    attribution_repository, audit_repository = create_repositories()

    current_time = datetime.now(timezone.utc)

    authorisation = DisclosureAuthorisation(
        authorisation_id="court-order-future",
        investigator_reference="investigator-001",
        issuing_authority="Crown Court",
        jurisdiction="GB",
        purpose="criminal-investigation",
        issued_at=current_time + timedelta(hours=1),
        expires_at=current_time + timedelta(hours=2),
        provider_id="gap-demo-provider",
    )

    with pytest.raises(
        DisclosureDeniedError,
        match="The authorisation is not yet valid.",
    ):
        disclose_attribution_record(
            generation_id="gid_" + "a" * 64,
            authorisation=authorisation,
            attribution_repository=attribution_repository,
            audit_repository=audit_repository,
        )

    assert audit_repository.count() == 1
    assert audit_repository.list_all()[0].approved is False


def test_wrong_provider_authorisation_is_denied() -> None:
    attribution_repository, audit_repository = create_repositories()

    authorisation = create_valid_authorisation(provider_id="different-provider")

    with pytest.raises(
        DisclosureDeniedError,
        match="The authorisation does not apply to this provider.",
    ):
        disclose_attribution_record(
            generation_id="gid_" + "a" * 64,
            authorisation=authorisation,
            attribution_repository=attribution_repository,
            audit_repository=audit_repository,
        )

    assert audit_repository.count() == 1

    audit_record = audit_repository.list_all()[0]

    assert audit_record.approved is False
    assert audit_record.denial_reason == (
        "The authorisation does not apply to this provider."
    )


def test_unsupported_purpose_is_denied() -> None:
    attribution_repository, audit_repository = create_repositories()

    authorisation = create_valid_authorisation(purpose="unsupported-purpose")

    with pytest.raises(
        DisclosureDeniedError,
        match="The disclosure purpose is not supported.",
    ):
        disclose_attribution_record(
            generation_id="gid_" + "a" * 64,
            authorisation=authorisation,
            attribution_repository=attribution_repository,
            audit_repository=audit_repository,
        )

    assert audit_repository.count() == 1
    assert audit_repository.list_all()[0].approved is False


def test_expiry_before_issue_time_is_denied() -> None:
    attribution_repository, audit_repository = create_repositories()

    current_time = datetime.now(timezone.utc)

    authorisation = DisclosureAuthorisation(
        authorisation_id="court-order-invalid-range",
        investigator_reference="investigator-001",
        issuing_authority="Crown Court",
        jurisdiction="GB",
        purpose="criminal-investigation",
        issued_at=current_time,
        expires_at=current_time - timedelta(minutes=1),
        provider_id="gap-demo-provider",
    )

    with pytest.raises(
        DisclosureDeniedError,
        match="The authorisation expiry must be after its issue time.",
    ):
        disclose_attribution_record(
            generation_id="gid_" + "a" * 64,
            authorisation=authorisation,
            attribution_repository=attribution_repository,
            audit_repository=audit_repository,
        )

    assert audit_repository.count() == 1
    assert audit_repository.list_all()[0].approved is False


def test_naive_authorisation_timestamps_are_denied() -> None:
    attribution_repository, audit_repository = create_repositories()

    current_time = datetime.now()

    authorisation = DisclosureAuthorisation(
        authorisation_id="court-order-naive",
        investigator_reference="investigator-001",
        issuing_authority="Crown Court",
        jurisdiction="GB",
        purpose="criminal-investigation",
        issued_at=current_time,
        expires_at=current_time + timedelta(hours=1),
        provider_id="gap-demo-provider",
    )

    with pytest.raises(
        DisclosureDeniedError,
        match=("Authorisation timestamps must include timezone information."),
    ):
        disclose_attribution_record(
            generation_id="gid_" + "a" * 64,
            authorisation=authorisation,
            attribution_repository=attribution_repository,
            audit_repository=audit_repository,
        )

    assert audit_repository.count() == 1
    assert audit_repository.list_all()[0].approved is False
