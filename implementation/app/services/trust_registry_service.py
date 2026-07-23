from dataclasses import dataclass
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
from app.services.registry_authority_repository import RegistryAuthorityRepository
from app.services.trust_attestation_repository import TrustAttestationRepository
from app.services.trust_attestation_service import (
    issue_trust_decision_attestation,
    verify_trust_attestation_details,
)


class InvalidTrustTransitionError(ValueError):
    """
    Raised when a provider trust-status transition is not permitted.
    """


class TrustDecisionChronologyError(ValueError):
    """
    Raised when a decision predates the provider's latest stored decision.
    """


@dataclass(frozen=True, slots=True)
class ProviderTrustEvaluation:
    provider_status: ProviderTrustStatus
    provider_approved: bool
    attestation_present: bool
    attestation_valid: bool
    registry_authority_id: str | None
    registry_authority_trusted: bool
    authority_key_id: str | None
    authority_key_status: str | None
    trust_decision_id: str | None
    trust_attestation_id: str | None
    trust_failure_reason: str | None
    trusted: bool


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
        authority_repository: RegistryAuthorityRepository | None = None,
        attestation_repository: TrustAttestationRepository | None = None,
        default_authority_id: str | None = None,
    ) -> None:
        self._trust_repository = trust_repository
        self._application_repository = application_repository
        self._authority_repository = authority_repository
        self._attestation_repository = attestation_repository
        self._default_authority_id = default_authority_id

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
        if self._authority_repository is None or self._attestation_repository is None:
            return self.get_current_status(provider_id) == "approved"
        return self.evaluate_provider_trust(provider_id).trusted

    def get_attestation_for_decision(self, decision_id: str):
        if self._attestation_repository is None:
            return None
        return self._attestation_repository.get_by_decision(decision_id)

    def get_current_attestation(self, provider_id: str):
        decision = self.get_current_decision(provider_id)
        if decision is None:
            return None
        return self.get_attestation_for_decision(decision.decision_id)

    def list_attestation_history(self, provider_id: str):
        if self._attestation_repository is None:
            return []
        return self._attestation_repository.list_for_provider(provider_id)

    def evaluate_provider_trust(self, provider_id: str) -> ProviderTrustEvaluation:
        decision = self.get_current_decision(provider_id)
        provider_status = self.get_current_status(provider_id)
        approved = provider_status == "approved"
        if not approved:
            return ProviderTrustEvaluation(
                provider_status,
                False,
                False,
                False,
                None,
                False,
                None,
                None,
                decision.decision_id if decision else None,
                None,
                "provider-not-approved",
                False,
            )
        attestation = self.get_current_attestation(provider_id)
        if attestation is None:
            return ProviderTrustEvaluation(
                provider_status,
                True,
                False,
                False,
                None,
                False,
                None,
                None,
                decision.decision_id if decision else None,
                None,
                "missing-trust-attestation",
                False,
            )
        payload = attestation.payload
        matches = decision is not None and all(
            (
                payload.decision_id == decision.decision_id,
                payload.provider_id == decision.provider_id,
                payload.status == decision.status,
                payload.decision_authority == decision.authority,
                payload.reason == decision.reason,
                payload.decided_at == decision.decided_at,
            )
        )
        if not matches:
            return ProviderTrustEvaluation(
                provider_status,
                True,
                True,
                False,
                payload.registry_authority_id,
                False,
                attestation.proof.key_id,
                None,
                decision.decision_id,
                payload.attestation_id,
                "attestation-decision-mismatch",
                False,
            )
        if self._authority_repository is None:
            verification = None
        else:
            verification = verify_trust_attestation_details(
                attestation, self._authority_repository
            )
        if verification is None or not verification.valid:
            reason = (
                verification.failure_reason
                if verification is not None
                else "unknown-registry-authority"
            )
            return ProviderTrustEvaluation(
                provider_status,
                True,
                True,
                False,
                payload.registry_authority_id,
                reason != "unknown-registry-authority",
                attestation.proof.key_id,
                verification.key_status if verification else None,
                decision.decision_id,
                payload.attestation_id,
                reason,
                False,
            )
        return ProviderTrustEvaluation(
            provider_status,
            True,
            True,
            True,
            verification.authority_id,
            True,
            verification.key_id,
            verification.key_status,
            decision.decision_id,
            payload.attestation_id,
            None,
            True,
        )

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

        attestation = None
        if (
            self._authority_repository is not None
            and self._attestation_repository is not None
            and self._default_authority_id is not None
        ):
            authority = self._authority_repository.get(self._default_authority_id)
            attestation = issue_trust_decision_attestation(
                decision, authority, issued_at=decision_time
            )
        self._trust_repository.add(decision)
        if attestation is not None:
            self._attestation_repository.add(attestation)
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
