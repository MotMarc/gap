from datetime import datetime, timezone
from uuid import uuid4

from app.domain.provider_application import ProviderOnboardingApplication
from app.domain.provider_trust import (
    ProviderTrustDecision,
    ProviderTrustStatus,
)
from app.services.provider_application_repository import (
    DuplicateProviderApplicationError,
    ProviderApplicationRepository,
)
from app.services.trust_registry_repository import TrustRegistryRepository


class InvalidTrustTransitionError(ValueError):
    """
    Raised when a provider trust-status transition is not permitted.
    """


class TrustDecisionChronologyError(ValueError):
    """
    Raised when a decision predates the provider's latest stored decision.
    """


ALLOWED_TRUST_TRANSITIONS: dict[
    ProviderTrustStatus,
    set[ProviderTrustStatus],
] = {
    "self-declared": {"applicant"},
    "applicant": {"approved", "removed"},
    "approved": {"suspended", "removed"},
    "suspended": {"approved", "removed"},
    "removed": set(),
}


class TrustRegistryService:
    """
    Coordinates provider onboarding and authoritative trust decisions.
    """

    def __init__(
        self,
        trust_repository: TrustRegistryRepository,
        application_repository: ProviderApplicationRepository,
    ) -> None:
        self._trust_repository = trust_repository
        self._application_repository = application_repository

    def get_current_decision(
        self,
        provider_id: str,
    ) -> ProviderTrustDecision | None:
        return self._trust_repository.latest_for_provider(provider_id)

    def get_current_status(
        self,
        provider_id: str,
    ) -> ProviderTrustStatus:
        decision = self.get_current_decision(provider_id)

        if decision is None:
            return "self-declared"

        return decision.status

    def is_trusted(
        self,
        provider_id: str,
    ) -> bool:
        return self.get_current_status(provider_id) == "approved"

    def list_decision_history(
        self,
        provider_id: str,
    ) -> list[ProviderTrustDecision]:
        return sorted(
            self._trust_repository.list_for_provider(provider_id),
            key=lambda decision: decision.decided_at,
        )

    def record_decision(
        self,
        provider_id: str,
        status: ProviderTrustStatus,
        authority: str,
        reason: str,
        *,
        decided_at: datetime | None = None,
        decision_id: str | None = None,
    ) -> ProviderTrustDecision:
        current_decision = self.get_current_decision(provider_id)
        current_status = (
            current_decision.status if current_decision is not None else "self-declared"
        )

        allowed_statuses = ALLOWED_TRUST_TRANSITIONS[current_status]

        if status not in allowed_statuses:
            raise InvalidTrustTransitionError(
                f"Invalid provider trust transition: {current_status} -> {status}"
            )

        decision_time = decided_at or datetime.now(timezone.utc)

        if decision_time.tzinfo is None:
            raise ValueError("Trust decision timestamps must be timezone-aware.")

        if current_decision is not None and decision_time < current_decision.decided_at:
            raise TrustDecisionChronologyError(
                "A trust decision cannot predate the provider's latest decision."
            )

        decision = ProviderTrustDecision(
            decision_id=decision_id or f"td_{uuid4().hex}",
            provider_id=provider_id,
            status=status,
            authority=authority,
            reason=reason,
            decided_at=decision_time,
        )

        self._trust_repository.add(decision)
        self._finalise_active_application(provider_id, status)

        return decision

    def submit_application(
        self,
        provider_id: str,
        provider_name: str,
        contact_reference: str,
        *,
        submitted_at: datetime | None = None,
        application_id: str | None = None,
    ) -> ProviderOnboardingApplication:
        current_status = self.get_current_status(provider_id)

        if current_status != "self-declared":
            raise InvalidTrustTransitionError(
                "Only self-declared providers may submit an onboarding "
                f"application. Current status: {current_status}"
            )

        if self._application_repository.active_for_provider(provider_id):
            raise DuplicateProviderApplicationError(
                "An active onboarding application already exists for provider: "
                f"{provider_id}"
            )

        submission_time = submitted_at or datetime.now(timezone.utc)

        application = ProviderOnboardingApplication(
            application_id=application_id or f"pa_{uuid4().hex}",
            provider_id=provider_id,
            provider_name=provider_name,
            contact_reference=contact_reference,
            submitted_at=submission_time,
            status="submitted",
        )

        self._application_repository.add(application)

        self.record_decision(
            provider_id=provider_id,
            status="applicant",
            authority="GAP Onboarding Service",
            reason="Provider submitted an onboarding application.",
            decided_at=submission_time,
        )

        return application

    def _finalise_active_application(
        self,
        provider_id: str,
        status: ProviderTrustStatus,
    ) -> None:
        application = self._application_repository.active_for_provider(provider_id)

        if application is None:
            return

        if status == "approved":
            self._application_repository.update_status(
                application.application_id,
                "approved",
            )
        elif status == "removed":
            self._application_repository.update_status(
                application.application_id,
                "rejected",
            )
