import base64
from binascii import Error as Base64DecodeError
from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.core.provider_adapters import provider_adapter_repository
from app.core.provider_config import provider_repository
from app.core.repositories import (
    attribution_repository,
    disclosure_audit_repository,
    provider_application_repository,
    trust_registry_repository,
    trust_registry_service,
    trust_attestation_repository,
    federation_bundle_repository,
    federated_trust_service,
    transparency_log_repository,
    witness_statement_repository,
    checkpoint_gossip_repository,
)
from app.core.transparency_log_config import (
    REFERENCE_TRANSPARENCY_LOG,
    TRUSTED_TRANSPARENCY_LOGS,
)
from app.core.registry_authority_config import registry_authority_repository
from app.crypto.provider_keys import load_private_key
from app.domain.disclosure_authorisation import DisclosureAuthorisation
from app.domain.generated_artifact import GeneratedArtifact
from app.domain.provider_trust import ProviderTrustDecision
from app.schemas.generation_credential import GenerationCredential
from app.schemas.protocol_api import (
    AttributionDisclosureResponse,
    DisclosureAuditResponse,
    DisclosureRequest,
    GenerateArtifactRequest,
    GenerateArtifactResponse,
    IssueCredentialRequest,
    VerificationResponse,
    VerifyCredentialRequest,
)
from app.schemas.provider_identity import ProviderIdentityDocument
from app.schemas.registry_authority import (
    RegistryAuthorityIdentityDocument,
    RegistryAuthoritySummaryResponse,
)
from app.schemas.trust_attestation import TrustDecisionAttestation
from app.schemas.federation_bundle import (
    FederationBundle,
    FederationBundleVerificationResult,
)
from app.schemas.signed_tree_head import SignedTreeHead
from app.schemas.transparency_log import TransparencyLogIdentityDocument
from app.schemas.transparency_proof import (
    ConsistencyVerificationRequest,
    ConsistencyVerificationResult,
    InclusionVerificationRequest,
    InclusionVerificationResult,
    TreeHeadComparisonRequest,
)
from app.services.federation_bundle_service import (
    calculate_bundle_digest,
    verify_federation_bundle,
)
from app.services.federation_bundle_repository import FederationBundleNotFoundError
from app.services.transparency_log_repository import (
    TransparencyEntryNotFoundError,
    TransparencyLogRepositoryError,
    TransparencyTreeHeadNotFoundError,
)
from app.services.transparency_log_identity_service import (
    create_transparency_log_identity_document,
)
from app.services.transparency_verification_service import (
    verify_consistency,
    verify_inclusion,
)
from app.schemas.trust_registry import (
    ProviderApplicationRequest,
    ProviderApplicationResponse,
    ProviderSummaryResponse,
    ProviderTrustDecisionResponse,
    ProviderTrustResponse,
    TrustRegistryEntryResponse,
)
from app.services.artifact_service import create_artifact_descriptor
from app.services.attribution_repository import AttributionRecordNotFoundError
from app.services.attribution_service import (
    create_provider_attribution_record,
)
from app.services.disclosure_service import (
    DisclosureDeniedError,
    disclose_attribution_record,
)
from app.services.generation_credential_service import (
    create_credential_payload,
    issue_generation_credential,
)
from app.services.generation_event_service import create_generation_event
from app.services.provider_adapter_repository import (
    ProviderAdapterNotFoundError,
)
from app.services.provider_application_repository import (
    DuplicateProviderApplicationError,
)
from app.services.provider_identity_service import (
    create_provider_identity_document,
)
from app.services.provider_repository import ProviderNotFoundError
from app.services.registry_authority_identity_service import (
    create_registry_authority_identity_document,
)
from app.services.registry_authority_repository import RegistryAuthorityNotFoundError
from app.services.trust_attestation_repository import TrustAttestationNotFoundError
from app.services.trust_registry_service import InvalidTrustTransitionError
from app.services.verification_service import (
    verify_generation_credential_details,
)
from app.core.transparency_witness_config import transparency_witness_repository
from app.schemas.checkpoint_gossip import (
    CheckpointGossipPackage,
    GossipMonitorResult,
)
from app.schemas.transparency_witness import TransparencyWitnessIdentityDocument
from app.schemas.witness_statement import (
    WitnessStatement,
    WitnessStatementVerificationResult,
)
from app.services.checkpoint_gossip_service import verify_checkpoint_gossip_package
from app.services.transparency_witness_identity_service import (
    create_transparency_witness_identity_document,
)
from app.services.transparency_witness_service import verify_witness_statement
from app.services.witness_quorum_service import (
    WitnessQuorumPolicy,
    WitnessQuorumResult,
    evaluate_witness_quorum,
)


router = APIRouter(
    tags=["GAP Protocol"],
)

DEFAULT_WITNESS_POLICY = WitnessQuorumPolicy(required_witness_count=1)


def get_provider_document(
    provider_id: str,
) -> ProviderIdentityDocument:
    try:
        provider = provider_repository.get(provider_id)
    except ProviderNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return create_provider_identity_document(
        provider=provider,
    )


def get_public_provider_name(
    provider_id: str,
) -> str:
    try:
        return provider_repository.get(provider_id).provider_name
    except ProviderNotFoundError:
        applications = provider_application_repository.list_for_provider(provider_id)

        if applications:
            return max(
                applications,
                key=lambda application: application.submitted_at,
            ).provider_name

        return provider_id


def create_trust_decision_response(
    decision: ProviderTrustDecision,
) -> ProviderTrustDecisionResponse:
    return ProviderTrustDecisionResponse(
        decision_id=decision.decision_id,
        provider_id=decision.provider_id,
        status=decision.status,
        authority=decision.authority,
        reason=decision.reason,
        decided_at=decision.decided_at,
    )


def create_provider_trust_response(
    provider_id: str,
) -> ProviderTrustResponse:
    history = trust_registry_service.list_decision_history(provider_id)
    latest_decision = history[-1] if history else None
    trust_status = trust_registry_service.get_current_status(provider_id)
    evaluation = trust_registry_service.evaluate_provider_trust(provider_id)
    attestation = trust_registry_service.get_current_attestation(provider_id)
    federation = federated_trust_service.evaluate(provider_id)
    transparency_sources = [asdict(source) for source in federation.authority_sources]

    return ProviderTrustResponse(
        provider_id=provider_id,
        provider_name=get_public_provider_name(provider_id),
        status=trust_status,
        trusted=federation.trusted,
        latest_decision=(
            create_trust_decision_response(latest_decision)
            if latest_decision is not None
            else None
        ),
        decision_history=[
            create_trust_decision_response(decision) for decision in history
        ],
        trust_attestation_id=evaluation.trust_attestation_id,
        trust_attestation_present=evaluation.attestation_present,
        trust_attestation_valid=evaluation.attestation_valid,
        registry_authority_id=evaluation.registry_authority_id,
        registry_authority_trusted=evaluation.registry_authority_trusted,
        authority_key_id=evaluation.authority_key_id,
        authority_key_status=evaluation.authority_key_status,
        attestation_issued_at=attestation.payload.issued_at if attestation else None,
        trust_failure_reason=evaluation.trust_failure_reason,
        effective_status=federation.effective_status,
        federation_conflict=federation.federation_conflict,
        federation_source_count=federation.source_count,
        federation_sources=[asdict(source) for source in federation.authority_sources],
        federation_failure_reason=federation.failure_reason,
        transparency_verified=federation.trusted
        and all(
            source.transparency_verified for source in federation.authority_sources
        ),
        transparency_sources=transparency_sources,
        transparency_failure_reason=(
            None
            if federation.trusted
            else next(
                (
                    source.transparency_failure_reason
                    for source in federation.authority_sources
                    if not source.transparency_verified
                ),
                None,
            )
        ),
    )


def require_approved_provider(
    provider_id: str,
) -> None:
    evaluation = federated_trust_service.evaluate(provider_id)
    if not evaluation.trusted:
        status_label = (
            evaluation.effective_status
            or trust_registry_service.get_current_status(provider_id)
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Provider {provider_id} cannot issue credentials: "
                f"{evaluation.failure_reason} "
                f"(status: {status_label})."
            ),
        )


def issue_credential_for_artifact(
    provider_id: str,
    account_reference: str,
    prompt: str,
    retention_days: int,
    artifact: GeneratedArtifact,
) -> GenerationCredential:
    try:
        provider = provider_repository.get(provider_id)
    except ProviderNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    require_approved_provider(provider_id)

    signing_key = provider.active_signing_key

    if signing_key.private_key_path is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The provider active signing key is unavailable.",
        )

    event = create_generation_event(
        provider_id=provider.provider_id,
        model_id=artifact.model_id,
    )

    try:
        attribution_record = create_provider_attribution_record(
            event=event,
            account_reference=account_reference,
            prompt=prompt,
            retention_days=retention_days,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    attribution_repository.add(attribution_record)

    artifact_descriptor = create_artifact_descriptor(
        artifact=artifact.content,
        media_type=artifact.media_type,
    )

    payload = create_credential_payload(
        event=event,
        artifacts=[artifact_descriptor],
    )

    private_key = load_private_key(
        signing_key.private_key_path,
    )

    return issue_generation_credential(
        payload=payload,
        key_id=signing_key.key_id,
        private_key=private_key,
    )


@router.get(
    "/providers",
    response_model=list[ProviderSummaryResponse],
)
def list_providers() -> list[ProviderSummaryResponse]:
    return [
        ProviderSummaryResponse(
            provider_id=provider.provider_id,
            provider_name=provider.provider_name,
            active_key_id=provider.active_key_id,
            published_key_count=len(provider.signing_keys),
            trust_status=trust_registry_service.get_current_status(
                provider.provider_id
            ),
            provider_trusted=trust_registry_service.is_trusted(provider.provider_id),
        )
        for provider in provider_repository.list_all()
    ]


@router.get(
    "/trust-registry",
    response_model=list[TrustRegistryEntryResponse],
)
def list_trust_registry() -> list[TrustRegistryEntryResponse]:
    provider_ids = {provider.provider_id for provider in provider_repository.list_all()}
    provider_ids.update(
        decision.provider_id for decision in trust_registry_repository.list_all()
    )
    provider_ids.update(
        application.provider_id
        for application in provider_application_repository.list_all()
    )

    entries = []

    for provider_id in sorted(provider_ids):
        latest_decision = trust_registry_service.get_current_decision(provider_id)
        trust_status = trust_registry_service.get_current_status(provider_id)
        evaluation = trust_registry_service.evaluate_provider_trust(provider_id)
        federation = federated_trust_service.evaluate(provider_id)

        entries.append(
            TrustRegistryEntryResponse(
                provider_id=provider_id,
                provider_name=get_public_provider_name(provider_id),
                status=trust_status,
                trusted=federation.trusted,
                latest_decision_id=(
                    latest_decision.decision_id if latest_decision is not None else None
                ),
                latest_decision_at=(
                    latest_decision.decided_at if latest_decision is not None else None
                ),
                trust_attestation_id=evaluation.trust_attestation_id,
                trust_attestation_valid=evaluation.attestation_valid,
                registry_authority_id=evaluation.registry_authority_id,
                registry_authority_trusted=evaluation.registry_authority_trusted,
                authority_key_id=evaluation.authority_key_id,
                authority_key_status=evaluation.authority_key_status,
                effective_status=federation.effective_status,
                federation_conflict=federation.federation_conflict,
                federation_source_count=federation.source_count,
                federation_sources=[
                    asdict(source) for source in federation.authority_sources
                ],
                federation_failure_reason=federation.failure_reason,
                transparency_verified=federation.trusted
                and all(
                    source.transparency_verified
                    for source in federation.authority_sources
                ),
                transparency_sources=[
                    asdict(source) for source in federation.authority_sources
                ],
                transparency_failure_reason=next(
                    (
                        source.transparency_failure_reason
                        for source in federation.authority_sources
                        if not source.transparency_verified
                    ),
                    None,
                ),
            )
        )

    return entries


@router.get(
    "/providers/{provider_id}/trust",
    response_model=ProviderTrustResponse,
)
def read_provider_trust(
    provider_id: str,
) -> ProviderTrustResponse:
    known_provider_ids = {
        provider.provider_id for provider in provider_repository.list_all()
    }
    known_provider_ids.update(
        decision.provider_id for decision in trust_registry_repository.list_all()
    )
    known_provider_ids.update(
        application.provider_id
        for application in provider_application_repository.list_all()
    )

    if provider_id not in known_provider_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown trust-registry provider: {provider_id}",
        )

    return create_provider_trust_response(provider_id)


@router.get(
    "/registry-authorities",
    response_model=list[RegistryAuthoritySummaryResponse],
)
def list_registry_authorities() -> list[RegistryAuthoritySummaryResponse]:
    return [
        RegistryAuthoritySummaryResponse(
            authority_id=authority.authority_id,
            authority_name=authority.authority_name,
            active_key_id=authority.active_key_id,
            published_key_count=len(authority.signing_keys),
            trusted_by_local_registry=True,
        )
        for authority in registry_authority_repository.list_all()
    ]


@router.get(
    "/registry-authorities/{authority_id}/.well-known/gap-registry.json",
    response_model=RegistryAuthorityIdentityDocument,
)
def read_registry_authority_identity(
    authority_id: str,
) -> RegistryAuthorityIdentityDocument:
    try:
        authority = registry_authority_repository.get(authority_id)
    except RegistryAuthorityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return create_registry_authority_identity_document(authority)


@router.get(
    "/trust-attestations",
    response_model=list[TrustDecisionAttestation],
)
def list_trust_attestations(
    provider_id: str | None = None,
) -> list[TrustDecisionAttestation]:
    if provider_id is not None:
        return trust_attestation_repository.list_for_provider(provider_id)
    return trust_attestation_repository.list_all()


@router.get(
    "/trust-attestations/{attestation_id}",
    response_model=TrustDecisionAttestation,
)
def read_trust_attestation(attestation_id: str) -> TrustDecisionAttestation:
    try:
        return trust_attestation_repository.get(attestation_id)
    except TrustAttestationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


def _bundle_summary(bundle: FederationBundle) -> dict:
    now = datetime.now(timezone.utc)
    latest = federation_bundle_repository.latest_for_authority(
        bundle.payload.registry_authority_id
    )
    expired = bundle.payload.expires_at <= now
    return {
        "bundle_id": bundle.payload.bundle_id,
        "registry_authority_id": bundle.payload.registry_authority_id,
        "sequence_number": bundle.payload.sequence_number,
        "issued_at": bundle.payload.issued_at,
        "expires_at": bundle.payload.expires_at,
        "previous_bundle_hash": bundle.payload.previous_bundle_hash,
        "bundle_hash": calculate_bundle_digest(bundle),
        "attestation_count": len(bundle.payload.attestations),
        "current": latest is not None
        and latest.payload.bundle_id == bundle.payload.bundle_id
        and not expired,
        "expired": expired,
        "valid": True,
        "signature_valid": True,
        "chain_valid": True,
        "replay_protected": True,
    }


@router.get("/federation/bundles")
def list_federation_bundles() -> list[dict]:
    return [_bundle_summary(item) for item in federation_bundle_repository.list_all()]


@router.get("/federation/bundles/{bundle_id}", response_model=FederationBundle)
def read_federation_bundle(bundle_id: str) -> FederationBundle:
    try:
        return federation_bundle_repository.get(bundle_id)
    except FederationBundleNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/federation/authorities/{authority_id}/chain")
def read_federation_chain(authority_id: str) -> list[dict]:
    bundles = federation_bundle_repository.list_for_authority(authority_id)
    if not bundles:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown federation bundle chain: {authority_id}",
        )
    return [_bundle_summary(item) for item in bundles]


@router.post(
    "/federation/bundles/verify",
    response_model=FederationBundleVerificationResult,
)
def verify_federation_bundle_stateless(
    bundle: FederationBundle,
) -> FederationBundleVerificationResult:
    return verify_federation_bundle(bundle, registry_authority_repository)


@router.get("/transparency/log")
def read_transparency_log() -> dict:
    latest = transparency_log_repository.latest_tree_head()
    return {
        "log_id": REFERENCE_TRANSPARENCY_LOG.log_id,
        "log_name": REFERENCE_TRANSPARENCY_LOG.log_name,
        "active_key_id": REFERENCE_TRANSPARENCY_LOG.active_key_id,
        "hash_algorithm": "SHA-256",
        "tree_algorithm": "GAP-RFC6962-SHA256-v1",
        "entry_count": transparency_log_repository.entry_count,
        "current_tree_size": transparency_log_repository.entry_count,
        "current_root_hash": transparency_log_repository.current_root(),
        "latest_tree_head_id": latest.payload.tree_head_id if latest else None,
        "latest_tree_head_timestamp": latest.payload.timestamp if latest else None,
        "trusted_locally": True,
        "invalid_runtime_object_count": (
            transparency_log_repository.invalid_runtime_object_count
        ),
        "consistency_status": "consistent",
    }


@router.get(
    "/transparency/log/.well-known/gap-transparency.json",
    response_model=TransparencyLogIdentityDocument,
)
def read_transparency_log_identity() -> TransparencyLogIdentityDocument:
    return create_transparency_log_identity_document(REFERENCE_TRANSPARENCY_LOG)


@router.get("/transparency/entries")
def list_transparency_entries(
    entry_type: str | None = None,
    source_authority_id: str | None = None,
    object_id: str | None = None,
    limit: int = 100,
):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    entries = transparency_log_repository.list_entries()
    if entry_type:
        entries = [item for item in entries if item.entry_type == entry_type]
    if source_authority_id:
        entries = [
            item for item in entries if item.source_authority_id == source_authority_id
        ]
    if object_id:
        entries = [item for item in entries if item.object_id == object_id]
    return [
        {"leaf_index": index, **item.model_dump(mode="json")}
        for index, item in enumerate(entries[:limit])
    ]


@router.get("/transparency/entries/{entry_id}")
def read_transparency_entry(entry_id: str):
    try:
        return transparency_log_repository.get(entry_id)
    except TransparencyEntryNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/transparency/tree-head", response_model=SignedTreeHead)
def read_current_tree_head() -> SignedTreeHead:
    tree_head = transparency_log_repository.latest_tree_head()
    if tree_head is None:
        raise HTTPException(status_code=404, detail="No signed tree head is available.")
    return tree_head


@router.get("/transparency/tree-heads", response_model=list[SignedTreeHead])
def list_tree_heads() -> list[SignedTreeHead]:
    return transparency_log_repository.list_tree_heads()


@router.get("/transparency/tree-heads/{tree_head_id}", response_model=SignedTreeHead)
def read_tree_head(tree_head_id: str) -> SignedTreeHead:
    try:
        return transparency_log_repository.get_tree_head(tree_head_id)
    except TransparencyTreeHeadNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/transparency/entries/{entry_id}/inclusion-proof")
def read_inclusion_proof(entry_id: str, tree_size: int | None = None):
    try:
        return transparency_log_repository.inclusion_proof(entry_id, tree_size)
    except (TransparencyEntryNotFoundError, TransparencyLogRepositoryError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/transparency/consistency-proof")
def read_consistency_proof(old_tree_size: int, new_tree_size: int):
    try:
        return transparency_log_repository.consistency_proof(
            old_tree_size, new_tree_size
        )
    except TransparencyLogRepositoryError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/transparency/witnesses")
def list_transparency_witnesses() -> dict:
    witnesses = [
        {
            "witness_id": witness.witness_id,
            "witness_name": witness.witness_name,
            "active_key_id": witness.active_key_id,
            "published_key_count": len(witness.signing_keys),
        }
        for witness in transparency_witness_repository.list_trusted_witnesses()
    ]
    return {"witnesses": witnesses, "count": len(witnesses)}


@router.get(
    "/transparency/witnesses/{witness_id}/.well-known/gap-witness.json",
    response_model=TransparencyWitnessIdentityDocument,
)
def read_transparency_witness_identity(
    witness_id: str,
) -> TransparencyWitnessIdentityDocument:
    try:
        witness = transparency_witness_repository.get(witness_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return create_transparency_witness_identity_document(witness)


@router.get(
    "/transparency/witness-statements",
)
def list_witness_statements(
    witness_id: str | None = None,
    log_id: str | None = None,
    tree_head_id: str | None = None,
    limit: int = 100,
) -> dict:
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    statements = witness_statement_repository.list_all()
    if witness_id:
        statements = [
            item for item in statements if item.payload.witness_id == witness_id
        ]
    if log_id:
        statements = [item for item in statements if item.payload.log_id == log_id]
    if tree_head_id:
        statements = [
            item for item in statements if item.payload.tree_head_id == tree_head_id
        ]
    records = statements[-limit:]
    return {
        "witness_statements": records,
        "count": len(records),
    }


@router.get(
    "/transparency/witness-statements/{statement_id}",
    response_model=WitnessStatement,
)
def read_witness_statement(statement_id: str) -> WitnessStatement:
    try:
        return witness_statement_repository.get(statement_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/transparency/witness-statements/verify",
    response_model=WitnessStatementVerificationResult,
)
def verify_witness_statement_stateless(
    statement: WitnessStatement, tree_head: SignedTreeHead
) -> WitnessStatementVerificationResult:
    return verify_witness_statement(
        statement, tree_head, transparency_witness_repository
    )


@router.get("/transparency/witness-quorum", response_model=WitnessQuorumResult)
def read_witness_quorum(tree_head_id: str | None = None) -> WitnessQuorumResult:
    try:
        tree_head = (
            transparency_log_repository.get_tree_head(tree_head_id)
            if tree_head_id
            else transparency_log_repository.latest_tree_head()
        )
    except TransparencyTreeHeadNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    if tree_head is None:
        raise HTTPException(status_code=404, detail="No signed tree head is available.")
    return evaluate_witness_quorum(
        tree_head,
        witness_statement_repository.list_by_tree_head(tree_head.payload.tree_head_id),
        transparency_witness_repository,
        DEFAULT_WITNESS_POLICY,
    )


@router.get(
    "/transparency/gossip/observations",
)
def list_gossip_observations(limit: int = 100) -> dict:
    try:
        observations = checkpoint_gossip_repository.list_all(limit)
        return {
            "observations": observations,
            "count": len(observations),
        }
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/transparency/gossip/observations/{gossip_id}",
    response_model=CheckpointGossipPackage,
)
def read_gossip_observation(gossip_id: str) -> CheckpointGossipPackage:
    try:
        return checkpoint_gossip_repository.get(gossip_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/transparency/gossip/verify",
    response_model=GossipMonitorResult,
)
def verify_gossip_stateless(
    package: CheckpointGossipPackage,
) -> GossipMonitorResult:
    return verify_checkpoint_gossip_package(
        package,
        TRUSTED_TRANSPARENCY_LOGS,
        transparency_witness_repository,
        DEFAULT_WITNESS_POLICY,
        checkpoint_gossip_repository.list_all(),
    )


def _current_gossip_status() -> GossipMonitorResult:
    packages = checkpoint_gossip_repository.list_all()
    if not packages:
        return GossipMonitorResult(
            checkpoint_gossip_consistent=False,
            consistency_unproven=True,
            failure_reason="no-gossip-observations",
        )
    current = packages[-1]
    return verify_checkpoint_gossip_package(
        current,
        TRUSTED_TRANSPARENCY_LOGS,
        transparency_witness_repository,
        DEFAULT_WITNESS_POLICY,
        packages[:-1],
    )


@router.get("/transparency/gossip/status")
def read_gossip_status() -> dict:
    status_result = _current_gossip_status()
    observations = checkpoint_gossip_repository.list_all()
    return {
        "status": status_result,
        "observation_count": len(observations),
    }


@router.get("/transparency/gossip/state", response_model=GossipMonitorResult)
def read_gossip_state() -> GossipMonitorResult:
    """Compatibility alias for the original Sprint 13 route."""
    return _current_gossip_status()


@router.post(
    "/transparency/verify-inclusion",
    response_model=InclusionVerificationResult,
)
def verify_inclusion_stateless(
    request: InclusionVerificationRequest,
) -> InclusionVerificationResult:
    return verify_inclusion(
        request.entry, request.tree_head, request.proof, TRUSTED_TRANSPARENCY_LOGS
    )


@router.post(
    "/transparency/verify-consistency",
    response_model=ConsistencyVerificationResult,
)
def verify_consistency_stateless(
    request: ConsistencyVerificationRequest,
) -> ConsistencyVerificationResult:
    return verify_consistency(
        request.old_tree_head,
        request.new_tree_head,
        request.proof,
        TRUSTED_TRANSPARENCY_LOGS,
    )


@router.post(
    "/transparency/compare-tree-heads",
    response_model=ConsistencyVerificationResult,
)
def compare_tree_heads(
    request: TreeHeadComparisonRequest,
) -> ConsistencyVerificationResult:
    old, new = request.old_tree_head.payload, request.new_tree_head.payload
    if old.log_id == new.log_id and old.tree_size == new.tree_size:
        if old.root_hash != new.root_hash:
            return ConsistencyVerificationResult(
                valid=False,
                split_view=True,
                failure_reason="split-view-detected",
            )
        return ConsistencyVerificationResult(valid=True, append_only=True)
    if request.proof is None:
        return ConsistencyVerificationResult(
            valid=False, failure_reason="consistency-proof-required"
        )
    return verify_consistency(
        request.old_tree_head,
        request.new_tree_head,
        request.proof,
        TRUSTED_TRANSPARENCY_LOGS,
    )


@router.post(
    "/provider-applications",
    response_model=ProviderApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_provider_application(
    request: ProviderApplicationRequest,
) -> ProviderApplicationResponse:
    try:
        application = trust_registry_service.submit_application(
            provider_id=request.provider_id,
            provider_name=request.provider_name,
            contact_reference=request.contact_reference,
        )
    except (
        DuplicateProviderApplicationError,
        InvalidTrustTransitionError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return ProviderApplicationResponse(
        application_id=application.application_id,
        provider_id=application.provider_id,
        provider_name=application.provider_name,
        application_status=application.status,
        trust_status=trust_registry_service.get_current_status(application.provider_id),
        submitted_at=application.submitted_at,
    )


@router.get(
    "/providers/{provider_id}/.well-known/gap.json",
    response_model=ProviderIdentityDocument,
)
def read_provider_identity(
    provider_id: str,
) -> ProviderIdentityDocument:
    return get_provider_document(provider_id)


@router.post(
    "/generations/create",
    response_model=GenerateArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_generated_artifact(
    request: GenerateArtifactRequest,
) -> GenerateArtifactResponse:
    """
    Generate an artifact through a registered provider adapter and issue its
    GAP Generation Credential.
    """

    try:
        adapter = provider_adapter_repository.get(
            request.provider_id,
        )
    except ProviderAdapterNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    require_approved_provider(request.provider_id)

    try:
        artifact = adapter.generate(request.prompt)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    credential = issue_credential_for_artifact(
        provider_id=request.provider_id,
        account_reference=request.account_reference,
        prompt=request.prompt,
        retention_days=request.retention_days,
        artifact=artifact,
    )

    return GenerateArtifactResponse(
        filename=artifact.filename,
        media_type=artifact.media_type,
        artifact_base64=base64.b64encode(artifact.content).decode("utf-8"),
        credential=credential,
    )


@router.post(
    "/credentials/issue",
    status_code=status.HTTP_201_CREATED,
)
def issue_credential(
    request: IssueCredentialRequest,
) -> GenerationCredential:
    try:
        artifact_bytes = base64.b64decode(
            request.artifact_base64,
            validate=True,
        )
    except (ValueError, Base64DecodeError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="artifact_base64 is not valid Base64.",
        ) from error

    if not artifact_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The decoded artifact cannot be empty.",
        )

    artifact = GeneratedArtifact(
        content=artifact_bytes,
        media_type=request.media_type,
        filename="externally-generated-artifact",
        model_id=request.model_id,
    )

    return issue_credential_for_artifact(
        provider_id=request.provider_id,
        account_reference=request.account_reference,
        prompt=request.prompt,
        retention_days=request.retention_days,
        artifact=artifact,
    )


@router.post(
    "/credentials/verify",
    response_model=VerificationResponse,
)
def verify_credential(
    request: VerifyCredentialRequest,
) -> VerificationResponse:
    credential = request.credential
    provider_id = credential.payload.provider.provider_id

    provider_document = get_provider_document(provider_id)

    cryptographic_verification = verify_generation_credential_details(
        credential=credential,
        provider_document=provider_document,
    )

    trust_evaluation = trust_registry_service.evaluate_provider_trust(provider_id)
    federation = federated_trust_service.evaluate(provider_id)
    trust_status = trust_evaluation.provider_status
    provider_trusted = federation.trusted
    cryptographic_valid = cryptographic_verification.valid
    transparency_sources = [asdict(source) for source in federation.authority_sources]
    transparent = [
        source
        for source in federation.authority_sources
        if source.transparency_verified
    ]
    transparency_verified = bool(transparent) and provider_trusted
    transparency_source = transparent[0] if transparent else None
    selected_tree_head = (
        transparency_log_repository.get_tree_head(
            transparency_source.transparency_tree_head_id
        )
        if transparency_source and transparency_source.transparency_tree_head_id
        else None
    )
    quorum = (
        evaluate_witness_quorum(
            selected_tree_head,
            witness_statement_repository.list_by_tree_head(
                selected_tree_head.payload.tree_head_id
            ),
            transparency_witness_repository,
            DEFAULT_WITNESS_POLICY,
        )
        if selected_tree_head
        else None
    )
    gossip_packages = checkpoint_gossip_repository.list_all()
    matching_gossip = next(
        (
            item
            for item in reversed(gossip_packages)
            if selected_tree_head
            and item.signed_tree_head.payload.tree_head_id
            == selected_tree_head.payload.tree_head_id
        ),
        None,
    )
    gossip = (
        verify_checkpoint_gossip_package(
            matching_gossip,
            TRUSTED_TRANSPARENCY_LOGS,
            transparency_witness_repository,
            DEFAULT_WITNESS_POLICY,
            [
                item
                for item in gossip_packages
                if item.gossip_id != matching_gossip.gossip_id
            ],
        )
        if matching_gossip
        else GossipMonitorResult(
            checkpoint_gossip_consistent=False,
            consistency_unproven=True,
            failure_reason="no-gossip-observations",
        )
    )
    valid = (
        cryptographic_valid
        and provider_trusted
        and transparency_verified
        and quorum is not None
        and quorum.quorum_met
        and gossip.checkpoint_gossip_consistent
        and not federation.federation_conflict
        and not gossip.split_view_detected
        and not gossip.witness_equivocation_detected
    )

    failure_reason = cryptographic_verification.failure_reason

    if cryptographic_valid and not provider_trusted:
        failure_reason = "provider-untrusted"

    return VerificationResponse(
        valid=valid,
        cryptographic_valid=cryptographic_valid,
        provider_trusted=provider_trusted,
        provider_trust_status=trust_status,
        trust_decision_id=(trust_evaluation.trust_decision_id),
        trust_attestation_present=trust_evaluation.attestation_present,
        trust_attestation_valid=trust_evaluation.attestation_valid,
        trust_attestation_id=trust_evaluation.trust_attestation_id,
        registry_authority_id=trust_evaluation.registry_authority_id,
        registry_authority_trusted=trust_evaluation.registry_authority_trusted,
        registry_authority_key_id=trust_evaluation.authority_key_id,
        registry_authority_key_status=trust_evaluation.authority_key_status,
        trust_failure_reason=trust_evaluation.trust_failure_reason,
        effective_provider_trust_status=federation.effective_status,
        federation_conflict=federation.federation_conflict,
        federation_source_count=federation.source_count,
        federation_authority_ids=[
            source.registry_authority_id for source in federation.authority_sources
        ],
        federation_bundle_ids=list(federation.bundle_ids),
        federation_sources=[asdict(source) for source in federation.authority_sources],
        federation_failure_reason=federation.failure_reason,
        transparency_verified=transparency_verified,
        transparency_log_id=(
            transparency_source.transparency_log_id if transparency_source else None
        ),
        transparency_log_trusted=(
            transparency_source.transparency_log_trusted
            if transparency_source
            else False
        ),
        transparency_entry_ids=[
            source.transparency_entry_id
            for source in transparent
            if source.transparency_entry_id
        ],
        transparency_tree_head_id=(
            transparency_source.transparency_tree_head_id
            if transparency_source
            else None
        ),
        transparency_tree_size=(
            transparency_source.transparency_tree_size if transparency_source else None
        ),
        transparency_root_hash=(
            transparency_source.transparency_root_hash if transparency_source else None
        ),
        transparency_tree_head_valid=(
            transparency_source.transparency_tree_head_valid
            if transparency_source
            else False
        ),
        transparency_inclusion_valid=(
            transparency_source.transparency_inclusion_valid
            if transparency_source
            else False
        ),
        transparency_consistency_valid=True,
        transparency_failure_reason=next(
            (
                source.transparency_failure_reason
                for source in federation.authority_sources
                if not source.transparency_verified
            ),
            None if transparency_verified else "transparency-entry-missing",
        ),
        transparency_sources=transparency_sources,
        witness_quorum_met=quorum.quorum_met if quorum else False,
        required_witness_count=quorum.required_witness_count if quorum else 1,
        valid_witness_count=quorum.valid_witness_count if quorum else 0,
        valid_witness_ids=quorum.valid_witness_ids if quorum else [],
        witness_failure_reason=quorum.failure_reason
        if quorum
        else "no-witness-statements",
        checkpoint_gossip_consistent=gossip.checkpoint_gossip_consistent,
        split_view_detected=gossip.split_view_detected,
        witness_equivocation_detected=gossip.witness_equivocation_detected,
        rollback_detected=gossip.rollback_detected,
        consistency_unproven=gossip.consistency_unproven,
        gossip_failure_reason=gossip.failure_reason,
        provider_id=provider_id,
        generation_id=credential.payload.generation.generation_id,
        credential_id=credential.payload.credential_id,
        key_id=credential.proof.key_id,
        algorithm=credential.proof.type,
        key_status=cryptographic_verification.key_status,
        failure_reason=failure_reason,
    )


@router.post(
    "/disclosures/resolve",
    response_model=AttributionDisclosureResponse,
)
def resolve_attribution_record(
    request: DisclosureRequest,
) -> AttributionDisclosureResponse:
    authorisation = DisclosureAuthorisation(
        authorisation_id=request.authorisation.authorisation_id,
        investigator_reference=request.authorisation.investigator_reference,
        issuing_authority=request.authorisation.issuing_authority,
        jurisdiction=request.authorisation.jurisdiction,
        purpose=request.authorisation.purpose,
        issued_at=request.authorisation.issued_at,
        expires_at=request.authorisation.expires_at,
        provider_id=request.authorisation.provider_id,
    )

    try:
        record = disclose_attribution_record(
            generation_id=request.generation_id,
            authorisation=authorisation,
            attribution_repository=attribution_repository,
            audit_repository=disclosure_audit_repository,
        )
    except AttributionRecordNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except DisclosureDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error.reason,
        ) from error

    return AttributionDisclosureResponse(
        generation_id=record.generation_id,
        provider_id=record.provider_id,
        account_reference=record.account_reference,
        prompt_hash=record.prompt_hash,
        model_id=record.model_id,
        created_at=record.created_at,
        retained_until=record.retained_until,
        retention_status=record.retention_status,
    )


@router.get(
    "/disclosures/audit",
    response_model=list[DisclosureAuditResponse],
)
def read_disclosure_audit_log() -> list[DisclosureAuditResponse]:
    return [
        DisclosureAuditResponse(
            disclosure_id=record.disclosure_id,
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            investigator_reference=record.investigator_reference,
            authorisation_id=record.authorisation_id,
            issuing_authority=record.issuing_authority,
            jurisdiction=record.jurisdiction,
            purpose=record.purpose,
            approved=record.approved,
            denial_reason=record.denial_reason,
            disclosed_at=record.disclosed_at,
        )
        for record in disclosure_audit_repository.list_all()
    ]
