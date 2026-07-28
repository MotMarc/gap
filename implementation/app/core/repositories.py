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
from app.services.federation_bundle_repository import FederationBundleRepository
from app.services.federated_trust_service import FederatedTrustService
from app.services.federation_file_service import load_accepted_bundle_directory
from pathlib import Path
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


attribution_repository = AttributionRepository()
disclosure_audit_repository = DisclosureAuditRepository()

provider_application_repository = ProviderApplicationRepository()
trust_registry_repository = TrustRegistryRepository()
trust_attestation_repository = TrustAttestationRepository()
federation_bundle_repository = FederationBundleRepository()
TRANSPARENCY_RUNTIME_DIRECTORY = (
    Path(__file__).resolve().parents[3] / "runtime" / "transparency"
)
transparency_log_repository = TransparencyLogRepository(
    REFERENCE_TRANSPARENCY_LOG, TRANSPARENCY_RUNTIME_DIRECTORY
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

FEDERATION_ACCEPTED_DIRECTORY = (
    Path(__file__).resolve().parents[3] / "runtime" / "federation" / "accepted"
)
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

WITNESS_RUNTIME_DIRECTORY = (
    Path(__file__).resolve().parents[3] / "runtime" / "witnesses"
)
GOSSIP_RUNTIME_DIRECTORY = Path(__file__).resolve().parents[3] / "runtime" / "gossip"
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
