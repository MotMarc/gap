from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.provider_trust import ProviderTrustStatus
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

    retention_days: int = Field(
        default=365,
        ge=1,
        le=3650,
    )


class GenerateArtifactRequest(BaseModel):
    provider_id: str = Field(
        default="gap-demo-provider",
        min_length=1,
        max_length=100,
    )

    account_reference: str = Field(
        min_length=1,
        max_length=200,
    )

    prompt: str = Field(
        min_length=1,
        max_length=10000,
    )

    retention_days: int = Field(
        default=365,
        ge=1,
        le=3650,
    )


class GenerateArtifactResponse(BaseModel):
    filename: str
    media_type: str
    artifact_base64: str
    credential: GenerationCredential


class VerifyCredentialRequest(BaseModel):
    credential: GenerationCredential


class VerificationResponse(BaseModel):
    valid: bool
    cryptographic_valid: bool
    provider_trusted: bool
    provider_trust_status: ProviderTrustStatus
    trust_decision_id: str | None = None
    trust_attestation_present: bool
    trust_attestation_valid: bool
    trust_attestation_id: str | None = None
    registry_authority_id: str | None = None
    registry_authority_trusted: bool
    registry_authority_key_id: str | None = None
    registry_authority_key_status: Literal["active", "retired", "revoked"] | None = None
    trust_failure_reason: str | None = None
    provider_id: str
    generation_id: str
    credential_id: str
    key_id: str
    algorithm: str
    key_status: Literal["active", "retired", "revoked"] | None = None
    failure_reason: str | None = None


class DisclosureAuthorisationRequest(BaseModel):
    authorisation_id: str = Field(
        min_length=1,
        max_length=200,
        examples=["court-order-001"],
    )

    investigator_reference: str = Field(
        min_length=1,
        max_length=200,
        examples=["investigator-001"],
    )

    issuing_authority: str = Field(
        min_length=1,
        max_length=300,
        examples=["Crown Court"],
    )

    jurisdiction: str = Field(
        min_length=1,
        max_length=100,
        examples=["GB"],
    )

    purpose: Literal[
        "criminal-investigation",
        "civil-proceedings",
        "regulatory-investigation",
        "national-security-investigation",
    ]

    issued_at: datetime
    expires_at: datetime

    provider_id: str = Field(
        min_length=1,
        max_length=100,
    )


class DisclosureRequest(BaseModel):
    generation_id: str = Field(min_length=1)
    authorisation: DisclosureAuthorisationRequest


class AttributionDisclosureResponse(BaseModel):
    generation_id: str
    provider_id: str
    account_reference: str
    prompt_hash: str
    model_id: str
    created_at: datetime
    retained_until: datetime
    retention_status: str


class DisclosureAuditResponse(BaseModel):
    disclosure_id: str
    generation_id: str
    provider_id: str
    investigator_reference: str
    authorisation_id: str
    issuing_authority: str
    jurisdiction: str
    purpose: str
    approved: bool
    denial_reason: str | None
    disclosed_at: datetime
