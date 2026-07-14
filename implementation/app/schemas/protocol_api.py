from pydantic import BaseModel, Field

from app.schemas.generation_credential import GenerationCredential


class IssueCredentialRequest(BaseModel):
    provider_id: str = Field(
        default="gap-demo-provider",
        min_length=1,
        max_length=100,
    )

    model_id: str = Field(
        min_length=1,
        max_length=200,
        examples=["demo-model-v1"],
    )

    media_type: str = Field(
        min_length=1,
        max_length=255,
        examples=["text/plain"],
    )

    artifact_base64: str = Field(
        min_length=1,
        description="Base64-encoded generated artifact bytes.",
    )


class VerifyCredentialRequest(BaseModel):
    credential: GenerationCredential


class VerificationResponse(BaseModel):
    valid: bool
    provider_id: str
    generation_id: str
    credential_id: str
    key_id: str
    algorithm: str
