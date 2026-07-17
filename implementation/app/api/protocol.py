import base64
from binascii import Error as Base64DecodeError

from fastapi import APIRouter, HTTPException, status

from app.core.provider_adapters import provider_adapter_repository
from app.core.provider_config import provider_repository
from app.core.repositories import (
    attribution_repository,
    disclosure_audit_repository,
)
from app.crypto.provider_keys import load_private_key, load_public_key
from app.domain.disclosure_authorisation import DisclosureAuthorisation
from app.domain.generated_artifact import GeneratedArtifact
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
from app.services.provider_identity_service import (
    create_provider_identity_document,
)
from app.services.provider_repository import ProviderNotFoundError
from app.services.verification_service import verify_generation_credential


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

    public_key = load_public_key(
        provider.public_key_path,
    )

    return create_provider_identity_document(
        provider_id=provider.provider_id,
        provider_name=provider.provider_name,
        key_id=provider.key_id,
        public_key=public_key,
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
        provider.private_key_path,
    )

    return issue_generation_credential(
        payload=payload,
        key_id=provider.key_id,
        private_key=private_key,
    )


@router.get("/providers")
def list_providers() -> list[dict[str, str]]:
    return [
        {
            "provider_id": provider.provider_id,
            "provider_name": provider.provider_name,
        }
        for provider in provider_repository.list_all()
    ]


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

    valid = verify_generation_credential(
        credential=credential,
        provider_document=provider_document,
    )

    return VerificationResponse(
        valid=valid,
        provider_id=provider_id,
        generation_id=credential.payload.generation.generation_id,
        credential_id=credential.payload.credential_id,
        key_id=credential.proof.key_id,
        algorithm=credential.proof.type,
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
