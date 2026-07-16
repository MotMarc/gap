import base64
from binascii import Error as Base64DecodeError

from fastapi import APIRouter, HTTPException, status

from app.core.provider_config import provider_repository
from app.core.repositories import (
    attribution_repository,
    disclosure_audit_repository,
)
from app.crypto.provider_keys import load_private_key, load_public_key
from app.schemas.protocol_api import (
    AttributionDisclosureResponse,
    DisclosureAuditResponse,
    DisclosureRequest,
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
from app.services.disclosure_service import disclose_attribution_record
from app.services.generation_credential_service import (
    create_credential_payload,
    issue_generation_credential,
)
from app.services.generation_event_service import create_generation_event
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
    """
    Resolve a provider and construct its public GAP identity document.
    """

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


@router.get(
    "/providers",
)
def list_providers() -> list[dict[str, str]]:
    """
    List providers available in the GAP reference implementation.
    """

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
    """
    Publish a provider's GAP identity and public verification keys.
    """

    return get_provider_document(provider_id)


@router.post(
    "/credentials/issue",
    status_code=status.HTTP_201_CREATED,
)
def issue_credential(
    request: IssueCredentialRequest,
):
    """
    Issue a signed Generation Credential for a Base64-encoded artifact.

    The public Generation Credential is returned to the caller.

    A private Provider Attribution Record is also created and stored using
    the Generation Identifier as its lookup key.
    """

    try:
        provider = provider_repository.get(
            request.provider_id,
        )
    except ProviderNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

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

    event = create_generation_event(
        provider_id=provider.provider_id,
        model_id=request.model_id,
    )

    attribution_record = create_provider_attribution_record(
        event=event,
        account_reference=request.account_reference,
        prompt=request.prompt,
    )

    attribution_repository.add(
        attribution_record,
    )

    artifact = create_artifact_descriptor(
        artifact=artifact_bytes,
        media_type=request.media_type,
    )

    payload = create_credential_payload(
        event=event,
        artifacts=[artifact],
    )

    private_key = load_private_key(
        provider.private_key_path,
    )

    return issue_generation_credential(
        payload=payload,
        key_id=provider.key_id,
        private_key=private_key,
    )


@router.post(
    "/credentials/verify",
    response_model=VerificationResponse,
)
def verify_credential(
    request: VerifyCredentialRequest,
) -> VerificationResponse:
    """
    Verify a Generation Credential using its provider's published identity.
    """

    credential = request.credential
    provider_id = credential.payload.provider.provider_id

    provider_document = get_provider_document(
        provider_id,
    )

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
    """
    Simulate lawful resolution of a private Provider Attribution Record.

    The current MVP accepts a non-empty investigator reference and
    authorisation reference as a simulation of lawful authority.
    """

    try:
        record = disclose_attribution_record(
            generation_id=request.generation_id,
            investigator_reference=request.investigator_reference,
            authorisation_reference=request.authorisation_reference,
            attribution_repository=attribution_repository,
            audit_repository=disclosure_audit_repository,
        )
    except AttributionRecordNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return AttributionDisclosureResponse(
        generation_id=record.generation_id,
        provider_id=record.provider_id,
        account_reference=record.account_reference,
        prompt_hash=record.prompt_hash,
        model_id=record.model_id,
        created_at=record.created_at,
        retention_status=record.retention_status,
    )


@router.get(
    "/disclosures/audit",
    response_model=list[DisclosureAuditResponse],
)
def read_disclosure_audit_log() -> list[DisclosureAuditResponse]:
    """
    Return the disclosure audit log.

    This endpoint is exposed publicly only for demonstration purposes.
    """

    return [
        DisclosureAuditResponse(
            disclosure_id=record.disclosure_id,
            generation_id=record.generation_id,
            provider_id=record.provider_id,
            investigator_reference=record.investigator_reference,
            authorisation_reference=record.authorisation_reference,
            disclosed_at=record.disclosed_at,
        )
        for record in disclosure_audit_repository.list_all()
    ]
