from datetime import datetime, timedelta, timezone
from app.core.provider_config import PROVIDERS
from app.core.settings import get_settings
from app.services.attribution_repository import AttributionRepository
from app.services.disclosure_audit_repository import DisclosureAuditRepository
from app.services.provider_application_repository import (
    ProviderApplicationRepository,
)
from app.services.trust_registry_repository import TrustRegistryRepository
from app.services.trust_registry_service import TrustRegistryService
from app.core.registry_authority_config import registry_authority_repository
from app.services.trust_attestation_repository import TrustAttestationRepository
from app.services.federation_bundle_repository import FederationBundleRepository
from app.services.federated_trust_service import FederatedTrustService
from app.services.federation_file_service import load_accepted_bundle_directory
from app.core.transparency_log_config import REFERENCE_TRANSPARENCY_LOG
from app.services.transparency_log_repository import TransparencyLogRepository
from app.core.transparency_witness_config import (
    REFERENCE_TRANSPARENCY_WITNESS,
)
from app.services.checkpoint_gossip_repository import CheckpointGossipRepository
from app.services.checkpoint_gossip_service import create_checkpoint_gossip_package
from app.services.transparency_log_identity_service import (
    create_transparency_log_identity_document,
)
from app.services.transparency_witness_service import issue_witness_statement
from app.services.witness_statement_repository import WitnessStatementRepository


settings = get_settings()
database = None
if settings.persistence_mode == "database":
    from app.database import Database, require_head
    from app.database.repositories import (
        SqlAttributionRepository,
        SqlCheckpointGossipRepository,
        SqlDisclosureAuditRepository,
        SqlFederationBundleRepository,
        SqlProviderApplicationRepository,
        SqlTransparencyLogRepository,
        SqlTrustAttestationRepository,
        SqlTrustRegistryRepository,
        SqlWitnessStatementRepository,
    )
    from app.database.uow import UnitOfWork

    database = Database(settings.database_url)
    require_head(database.engine)
    factory = database.session_factory
    attribution_repository = SqlAttributionRepository(factory)
    disclosure_audit_repository = SqlDisclosureAuditRepository(factory)
    provider_application_repository = SqlProviderApplicationRepository(factory)
    trust_registry_repository = SqlTrustRegistryRepository(factory)
    trust_attestation_repository = SqlTrustAttestationRepository(factory)
    federation_bundle_repository = SqlFederationBundleRepository(factory)
    transparency_log_repository = SqlTransparencyLogRepository(
        factory, REFERENCE_TRANSPARENCY_LOG
    )
else:
    attribution_repository = AttributionRepository()
    disclosure_audit_repository = DisclosureAuditRepository()
    provider_application_repository = ProviderApplicationRepository()
    trust_registry_repository = TrustRegistryRepository()
    trust_attestation_repository = TrustAttestationRepository()
    federation_bundle_repository = FederationBundleRepository()
    transparency_log_repository = TransparencyLogRepository(
        REFERENCE_TRANSPARENCY_LOG,
        settings.runtime_directory / "transparency",
    )
trust_registry_service = TrustRegistryService(
    trust_repository=trust_registry_repository,
    application_repository=provider_application_repository,
    authority_repository=registry_authority_repository,
    attestation_repository=trust_attestation_repository,
    default_authority_id="gap-reference-registry",
    transparency_repository=transparency_log_repository,
)
federated_trust_service = FederatedTrustService(
    local_trust_service=trust_registry_service,
    authority_repository=registry_authority_repository,
    bundle_repository=federation_bundle_repository,
    local_authority_id="gap-reference-registry",
    transparency_repository=transparency_log_repository,
)


SEED_APPLICATION_TIME = datetime(
    2026,
    7,
    27,
    tzinfo=timezone.utc,
)
SEED_APPROVAL_TIME = SEED_APPLICATION_TIME + timedelta(days=1)


def bootstrap_reference_state() -> dict[str, int]:
    existing = {
        decision.decision_id: decision
        for decision in trust_registry_repository.list_all()
    }
    created = 0
    for index, provider in enumerate(PROVIDERS, start=1):
        specifications = (
            (
                "applicant",
                SEED_APPLICATION_TIME,
                f"seed-application-{index}",
                "Existing provider entered the registry bootstrap review.",
            ),
            (
                "approved",
                SEED_APPROVAL_TIME,
                f"seed-approval-{index}",
                "Existing provider approved during registry bootstrap.",
            ),
        )
        for status, decided_at, decision_id, reason in specifications:
            current = existing.get(decision_id)
            if current is not None:
                compatible = (
                    current.provider_id == provider.provider_id
                    and current.status == status
                    and current.decided_at == decided_at
                    and current.reason == reason
                )
                if not compatible and settings.startup_strict_mode:
                    raise RuntimeError(f"Bootstrap divergence for {decision_id}.")
                continue
            if database is None:
                trust_registry_service.record_decision(
                    provider_id=provider.provider_id,
                    status=status,
                    authority="GAP Registry Bootstrap",
                    reason=reason,
                    decided_at=decided_at,
                    decision_id=decision_id,
                )
            else:
                with UnitOfWork(database.session_factory):
                    trust_registry_service.record_decision(
                        provider_id=provider.provider_id,
                        status=status,
                        authority="GAP Registry Bootstrap",
                        reason=reason,
                        decided_at=decided_at,
                        decision_id=decision_id,
                    )
            created += 1
    return {"created": created, "existing": len(existing)}


BOOTSTRAP_REPORT = bootstrap_reference_state()

FEDERATION_ACCEPTED_DIRECTORY = settings.runtime_directory / "federation" / "accepted"
(
    FEDERATION_LOADED_BUNDLE_COUNT,
    FEDERATION_INVALID_FILE_COUNT,
) = load_accepted_bundle_directory(
    FEDERATION_ACCEPTED_DIRECTORY,
    registry_authority_repository,
    federation_bundle_repository,
    transparency_log_repository,
)

latest_tree_head = transparency_log_repository.latest_tree_head()
if (
    latest_tree_head is None
    or latest_tree_head.payload.tree_size != transparency_log_repository.entry_count
    or latest_tree_head.payload.root_hash != transparency_log_repository.current_root()
):
    transparency_log_repository.create_current_tree_head()

WITNESS_RUNTIME_DIRECTORY = settings.runtime_directory / "witnesses"
GOSSIP_RUNTIME_DIRECTORY = settings.runtime_directory / "gossip"
if settings.persistence_mode == "database":
    witness_statement_repository = SqlWitnessStatementRepository(factory)
    checkpoint_gossip_repository = SqlCheckpointGossipRepository(factory)
else:
    witness_statement_repository = WitnessStatementRepository(WITNESS_RUNTIME_DIRECTORY)
    checkpoint_gossip_repository = CheckpointGossipRepository(GOSSIP_RUNTIME_DIRECTORY)


def record_reference_witness_evidence(tree_head) -> None:
    statements = witness_statement_repository.list_by_tree_head(
        tree_head.payload.tree_head_id
    )
    if not statements:
        statement = issue_witness_statement(
            REFERENCE_TRANSPARENCY_WITNESS,
            tree_head,
            create_transparency_log_identity_document(REFERENCE_TRANSPARENCY_LOG),
            observed_at=tree_head.payload.timestamp + timedelta(minutes=1),
            statement_id=f"gap-reference-statement-{tree_head.payload.tree_head_id}",
        )
        witness_statement_repository.add(statement)
        statements = [statement]
    packages = checkpoint_gossip_repository.list_all()
    if any(
        item.signed_tree_head.payload.tree_head_id == tree_head.payload.tree_head_id
        for item in packages
    ):
        return
    previous_package = packages[-1] if packages else None
    previous_head = (
        previous_package.signed_tree_head if previous_package is not None else None
    )
    proof = None
    if (
        previous_head is not None
        and previous_head.payload.tree_size <= tree_head.payload.tree_size
    ):
        proof = transparency_log_repository.consistency_proof(
            previous_head.payload.tree_size, tree_head.payload.tree_size
        )
    checkpoint_gossip_repository.add(
        create_checkpoint_gossip_package(
            tree_head,
            statements,
            previous_signed_tree_head=previous_head,
            consistency_proof_to_previous=proof,
            exported_at=tree_head.payload.timestamp + timedelta(minutes=2),
            gossip_id=f"gap-reference-gossip-{tree_head.payload.tree_head_id}",
        )
    )


latest_tree_head = transparency_log_repository.latest_tree_head()
if latest_tree_head is not None:
    record_reference_witness_evidence(latest_tree_head)
transparency_log_repository.on_tree_head_created = record_reference_witness_evidence
