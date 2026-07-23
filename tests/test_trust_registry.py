import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.core.repositories import trust_registry_service  # noqa: E402
from app.domain.provider_application import (  # noqa: E402
    ProviderOnboardingApplication,
)
from app.services.provider_application_repository import (  # noqa: E402
    DuplicateProviderApplicationError,
    ProviderApplicationRepository,
)
from app.services.trust_registry_repository import (  # noqa: E402
    TrustRegistryRepository,
)
from app.services.trust_registry_service import (  # noqa: E402
    InvalidTrustTransitionError,
    TrustDecisionChronologyError,
    TrustRegistryService,
)


def create_service() -> tuple[
    TrustRegistryService,
    TrustRegistryRepository,
    ProviderApplicationRepository,
]:
    trust_repository = TrustRegistryRepository()
    application_repository = ProviderApplicationRepository()
    service = TrustRegistryService(
        trust_repository=trust_repository,
        application_repository=application_repository,
    )

    return service, trust_repository, application_repository


def test_unknown_provider_is_self_declared() -> None:
    service, _, _ = create_service()

    assert service.get_current_status("new-provider") == "self-declared"
    assert service.is_trusted("new-provider") is False


def test_application_moves_provider_to_applicant() -> None:
    service, _, application_repository = create_service()

    application = service.submit_application(
        provider_id="new-provider",
        provider_name="New Provider",
        contact_reference="private-contact",
        submitted_at=datetime(2026, 7, 23, tzinfo=timezone.utc),
        application_id="application-001",
    )

    assert application.status == "submitted"
    assert service.get_current_status("new-provider") == "applicant"
    assert (
        application_repository.get("application-001").contact_reference
        == "private-contact"
    )


def test_duplicate_active_application_is_rejected() -> None:
    _, _, application_repository = create_service()
    submitted_at = datetime(2026, 7, 23, tzinfo=timezone.utc)

    first_application = ProviderOnboardingApplication(
        application_id="application-001",
        provider_id="new-provider",
        provider_name="New Provider",
        contact_reference="private-contact",
        submitted_at=submitted_at,
    )
    application_repository.add(first_application)

    duplicate_application = ProviderOnboardingApplication(
        application_id="application-002",
        provider_id="new-provider",
        provider_name="New Provider",
        contact_reference="other-private-contact",
        submitted_at=submitted_at,
    )

    with pytest.raises(DuplicateProviderApplicationError):
        application_repository.add(duplicate_application)


def test_applicant_can_be_approved() -> None:
    service, _, application_repository = create_service()
    submitted_at = datetime(2026, 7, 23, tzinfo=timezone.utc)

    application = service.submit_application(
        provider_id="new-provider",
        provider_name="New Provider",
        contact_reference="private-contact",
        submitted_at=submitted_at,
    )

    decision = service.record_decision(
        provider_id="new-provider",
        status="approved",
        authority="GAP Registry Authority",
        reason="Onboarding review completed successfully.",
        decided_at=submitted_at + timedelta(hours=1),
    )

    assert decision.status == "approved"
    assert service.is_trusted("new-provider") is True
    assert application_repository.get(application.application_id).status == ("approved")


def test_invalid_direct_approval_is_rejected() -> None:
    service, _, _ = create_service()

    with pytest.raises(InvalidTrustTransitionError):
        service.record_decision(
            provider_id="new-provider",
            status="approved",
            authority="GAP Registry Authority",
            reason="Invalid direct approval.",
        )


def test_approved_provider_can_be_suspended_and_restored() -> None:
    service, _, _ = create_service()
    submitted_at = datetime(2026, 7, 23, tzinfo=timezone.utc)

    service.submit_application(
        provider_id="new-provider",
        provider_name="New Provider",
        contact_reference="private-contact",
        submitted_at=submitted_at,
    )
    service.record_decision(
        provider_id="new-provider",
        status="approved",
        authority="GAP Registry Authority",
        reason="Approved.",
        decided_at=submitted_at + timedelta(hours=1),
    )
    service.record_decision(
        provider_id="new-provider",
        status="suspended",
        authority="GAP Registry Authority",
        reason="Temporary compliance review.",
        decided_at=submitted_at + timedelta(hours=2),
    )

    assert service.is_trusted("new-provider") is False

    service.record_decision(
        provider_id="new-provider",
        status="approved",
        authority="GAP Registry Authority",
        reason="Compliance review completed.",
        decided_at=submitted_at + timedelta(hours=3),
    )

    assert service.is_trusted("new-provider") is True


def test_removed_status_is_terminal() -> None:
    service, _, _ = create_service()
    submitted_at = datetime(2026, 7, 23, tzinfo=timezone.utc)

    service.submit_application(
        provider_id="new-provider",
        provider_name="New Provider",
        contact_reference="private-contact",
        submitted_at=submitted_at,
    )
    service.record_decision(
        provider_id="new-provider",
        status="removed",
        authority="GAP Registry Authority",
        reason="Application rejected.",
        decided_at=submitted_at + timedelta(hours=1),
    )

    with pytest.raises(InvalidTrustTransitionError):
        service.record_decision(
            provider_id="new-provider",
            status="applicant",
            authority="GAP Registry Authority",
            reason="Attempted re-entry.",
            decided_at=submitted_at + timedelta(hours=2),
        )


def test_decision_history_is_retained() -> None:
    service, _, _ = create_service()
    submitted_at = datetime(2026, 7, 23, tzinfo=timezone.utc)

    service.submit_application(
        provider_id="new-provider",
        provider_name="New Provider",
        contact_reference="private-contact",
        submitted_at=submitted_at,
    )
    service.record_decision(
        provider_id="new-provider",
        status="approved",
        authority="GAP Registry Authority",
        reason="Approved.",
        decided_at=submitted_at + timedelta(hours=1),
    )
    service.record_decision(
        provider_id="new-provider",
        status="suspended",
        authority="GAP Registry Authority",
        reason="Suspended.",
        decided_at=submitted_at + timedelta(hours=2),
    )

    history = service.list_decision_history("new-provider")

    assert [decision.status for decision in history] == [
        "applicant",
        "approved",
        "suspended",
    ]


def test_out_of_order_decision_is_rejected() -> None:
    service, _, _ = create_service()
    submitted_at = datetime(2026, 7, 23, tzinfo=timezone.utc)

    service.submit_application(
        provider_id="new-provider",
        provider_name="New Provider",
        contact_reference="private-contact",
        submitted_at=submitted_at,
    )

    with pytest.raises(TrustDecisionChronologyError):
        service.record_decision(
            provider_id="new-provider",
            status="approved",
            authority="GAP Registry Authority",
            reason="Out-of-order decision.",
            decided_at=submitted_at - timedelta(seconds=1),
        )


def test_existing_providers_are_seeded_as_approved() -> None:
    assert trust_registry_service.is_trusted("gap-demo-provider") is True
    assert trust_registry_service.is_trusted("aurora-ai") is True
    assert trust_registry_service.is_trusted("meridian-ai") is True
