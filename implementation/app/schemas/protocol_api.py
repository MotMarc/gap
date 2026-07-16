from datetime import datetime

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

    account_reference: str = Field(
        min_length=1,
        max_length=200,
        description="Private provider-side account reference.",
    )

    prompt: str = Field(
        min_length=1,
        max_length=10000,
        description="Prompt retained privately by the provider.",
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


class DisclosureRequest(BaseModel):
    generation_id: str = Field(min_length=1)
    investigator_reference: str = Field(
        min_length=1,
        max_length=200,
    )
    authorisation_reference: str = Field(
        min_length=1,
        max_length=200,
    )


class AttributionDisclosureResponse(BaseModel):
    generation_id: str
    provider_id: str
    account_reference: str
    prompt_hash: str
    model_id: str
    created_at: datetime
    retention_status: str


class DisclosureAuditResponse(BaseModel):
    disclosure_id: str
    generation_id: str
    provider_id: str
    investigator_reference: str
    authorisation_reference: str
    disclosed_at: datetime
