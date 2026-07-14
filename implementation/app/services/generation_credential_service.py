from app.crypto.credential_id import generate_credential_id
from app.domain.generation_event import GenerationEvent
from app.schemas.artifact import ArtifactDescriptor
from app.schemas.generation_credential import (
    CredentialGeneration,
    CredentialModel,
    CredentialProvider,
    GenerationCredentialPayload,
)


CURRENT_CREDENTIAL_VERSION = "0.0.1"


def create_credential_payload(
    event: GenerationEvent,
    key_id: str,
    artifacts: list[ArtifactDescriptor],
) -> GenerationCredentialPayload:
    """
    Create an unsigned Generation Credential payload.

    Signing will be implemented separately.
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
            key_id=key_id,
        ),
        model=CredentialModel(
            model_id=event.model_id,
        ),
        artifacts=artifacts,
    )
