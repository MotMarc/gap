from datetime import datetime, timedelta, timezone

from app.core.provider_config import PROVIDERS
from app.services.attribution_repository import AttributionRepository
from app.services.disclosure_audit_repository import DisclosureAuditRepository
from app.services.provider_application_repository import (
    ProviderApplicationRepository,
)
from app.services.trust_registry_repository import TrustRegistryRepository
from app.services.trust_registry_service import TrustRegistryService
from app.core.registry_authority_config import registry_authority_repository
from app.services.trust_attestation_repository import TrustAttestationRepository


attribution_repository = AttributionRepository()
disclosure_audit_repository = DisclosureAuditRepository()

provider_application_repository = ProviderApplicationRepository()
trust_registry_repository = TrustRegistryRepository()
trust_attestation_repository = TrustAttestationRepository()
trust_registry_service = TrustRegistryService(
    trust_repository=trust_registry_repository,
    application_repository=provider_application_repository,
    authority_repository=registry_authority_repository,
    attestation_repository=trust_attestation_repository,
    default_authority_id="gap-reference-registry",
)


SEED_APPLICATION_TIME = datetime(
    2026,
    1,
    1,
    tzinfo=timezone.utc,
)
SEED_APPROVAL_TIME = SEED_APPLICATION_TIME + timedelta(days=1)


for index, provider in enumerate(PROVIDERS, start=1):
    trust_registry_service.record_decision(
        provider_id=provider.provider_id,
        status="applicant",
        authority="GAP Registry Bootstrap",
        reason="Existing provider entered the registry bootstrap review.",
        decided_at=SEED_APPLICATION_TIME,
        decision_id=f"seed-application-{index}",
    )

    trust_registry_service.record_decision(
        provider_id=provider.provider_id,
        status="approved",
        authority="GAP Registry Bootstrap",
        reason="Existing provider approved during registry bootstrap.",
        decided_at=SEED_APPROVAL_TIME,
        decision_id=f"seed-approval-{index}",
    )
