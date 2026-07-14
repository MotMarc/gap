from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.artifact import ArtifactDescriptor


class CredentialProvider(BaseModel):
    provider_id: str = Field(
        min_length=1,
        max_length=100,
    )


class CredentialGeneration(BaseModel):
    generation_id: str
    created_at: datetime


class CredentialModel(BaseModel):
    model_id: str = Field(
        min_length=1,
        max_length=200,
    )


class GenerationCredentialPayload(BaseModel):
    version: str = "0.0.1"
    credential_id: str
    generation: CredentialGeneration
    provider: CredentialProvider
    model: CredentialModel
    artifacts: list[ArtifactDescriptor] = Field(min_length=1)


class GenerationCredentialProof(BaseModel):
    type: str = "Ed25519"
    key_id: str
    signature: str


class GenerationCredential(BaseModel):
    payload: GenerationCredentialPayload
    proof: GenerationCredentialProof
