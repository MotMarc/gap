import base64
from binascii import Error as Base64DecodeError

from fastapi import APIRouter, HTTPException, status

from app.core.provider_config import (
    KEY_ID,
    PRIVATE_KEY_PATH,
    PROVIDER_ID,
    PROVIDER_NAME,
    PUBLIC_KEY_PATH,
)
from app.crypto.provider_keys import load_private_key, load_public_key
from app.schemas.protocol_api import (
    IssueCredentialRequest,
    VerificationResponse,
    VerifyCredentialRequest,
)
from app.schemas.provider_identity import ProviderIdentityDocument
from app.services.artifact_service import create_artifact_descriptor
from app.services.generation_credential_service import (
    create_credential_payload,
    issue_generation_credential,
)
from app.services.generation_event_service import create_generation_event
from app.services.provider_identity_service import (
    create_provider_identity_document,
)
from app.services.verification_service import verify_generation_credential


router = APIRouter(
    tags=["GAP Protocol"],
)


def get_provider_document() -> ProviderIdentityDocument:
    public_key = load_public_key(PUBLIC_KEY_PATH)

    return create_provider_identity_document(
        provider_id=PROVIDER_ID,
        provider_name=PROVIDER_NAME,
        key_id=KEY_ID,
        public_key=public_key,
    )


@router.get(
    "/.well-known/gap.json",
    response_model=ProviderIdentityDocument,
)
def read_provider_identity() -> ProviderIdentityDocument:
    """
    Publish the demo provider's GAP identity and public verification key.
    """

    return get_provider_document()


@router.post(
    "/credentials/issue",
    status_code=status.HTTP_201_CREATED,
)
def issue_credential(
    request: IssueCredentialRequest,
):
    """
    Issue a signed Generation Credential for a Base64-encoded artifact.
    """

    if request.provider_id != PROVIDER_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reference provider cannot issue credentials for "
            "another provider identifier.",
        )

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
        provider_id=PROVIDER_ID,
        model_id=request.model_id,
    )

    artifact = create_artifact_descriptor(
        artifact=artifact_bytes,
        media_type=request.media_type,
    )

    payload = create_credential_payload(
        event=event,
        artifacts=[artifact],
    )

    private_key = load_private_key(PRIVATE_KEY_PATH)

    return issue_generation_credential(
        payload=payload,
        key_id=KEY_ID,
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
    Verify a Generation Credential using the provider's published identity.
    """

    credential = request.credential
    provider_document = get_provider_document()

    valid = verify_generation_credential(
        credential=credential,
        provider_document=provider_document,
    )

    return VerificationResponse(
        valid=valid,
        provider_id=credential.payload.provider.provider_id,
        generation_id=credential.payload.generation.generation_id,
        credential_id=credential.payload.credential_id,
        key_id=credential.proof.key_id,
        algorithm=credential.proof.type,
    )
