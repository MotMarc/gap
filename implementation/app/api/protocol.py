import base64
from binascii import Error as Base64DecodeError

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


router = APIRouter(
    tags=["GAP Protocol"],
)


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

    return ProviderTrustResponse(
        provider_id=provider_id,
        provider_name=get_public_provider_name(provider_id),
        status=trust_status,
        trusted=evaluation.trusted,
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
    )


def require_approved_provider(
    provider_id: str,
) -> None:
    evaluation = trust_registry_service.evaluate_provider_trust(provider_id)
    if not evaluation.trusted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Provider {provider_id} cannot issue credentials: "
                f"{evaluation.trust_failure_reason} "
                f"(status: {evaluation.provider_status})."
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

        entries.append(
            TrustRegistryEntryResponse(
                provider_id=provider_id,
                provider_name=get_public_provider_name(provider_id),
                status=trust_status,
                trusted=evaluation.trusted,
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
    trust_status = trust_evaluation.provider_status
    provider_trusted = trust_evaluation.trusted
    cryptographic_valid = cryptographic_verification.valid
    valid = cryptographic_valid and provider_trusted

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
