from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.crypto.canonical_json import canonicalise_model
from app.crypto.credential_id import generate_credential_id
from app.crypto.signatures import sign_payload
from app.domain.generation_event import GenerationEvent
from app.schemas.artifact import ArtifactDescriptor
from app.schemas.generation_credential import (
    CredentialGeneration,
    CredentialModel,
    CredentialProvider,
    GenerationCredential,
    GenerationCredentialPayload,
    GenerationCredentialProof,
)


CURRENT_CREDENTIAL_VERSION = "0.0.1"


def create_credential_payload(
    event: GenerationEvent,
    artifacts: list[ArtifactDescriptor],
) -> GenerationCredentialPayload:
    """
    Create an unsigned Generation Credential Payload.
    """

    return GenerationCredentialPayload(
        version=CURRENT_CREDENTIAL_VERSION,
        credential_id=generate_credential_id(),
        generation=CredentialGeneration(
            generation_id=event.generation_id,
            created_at=event.created_at,
        ),
        provider=CredentialProvider(
            provider_id=event.provider_id,
        ),
        model=CredentialModel(
            model_id=event.model_id,
        ),
        artifacts=artifacts,
    )


def issue_generation_credential(
    payload: GenerationCredentialPayload,
    key_id: str,
    private_key: Ed25519PrivateKey,
) -> GenerationCredential:
    """
    Sign a Generation Credential Payload and return a complete credential.
    """

    canonical_payload = canonicalise_model(payload)
    signature = sign_payload(
        payload=canonical_payload,
        private_key=private_key,
    )

    return GenerationCredential(
        payload=payload,
        proof=GenerationCredentialProof(
            type="Ed25519",
            key_id=key_id,
            signature=signature,
        ),
    )
