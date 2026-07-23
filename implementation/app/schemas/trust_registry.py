from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.provider_application import ProviderApplicationStatus
from app.domain.provider_trust import ProviderTrustStatus


class ProviderTrustDecisionResponse(BaseModel):
    decision_id: str
    provider_id: str
    status: ProviderTrustStatus
    authority: str
    reason: str
    decided_at: datetime


class ProviderTrustResponse(BaseModel):
    provider_id: str
    provider_name: str
    status: ProviderTrustStatus
    trusted: bool
    latest_decision: ProviderTrustDecisionResponse | None = None
    decision_history: list[ProviderTrustDecisionResponse]
    trust_attestation_id: str | None = None
    trust_attestation_present: bool = False
    trust_attestation_valid: bool = False
    registry_authority_id: str | None = None
    registry_authority_trusted: bool = False
    authority_key_id: str | None = None
    authority_key_status: Literal["active", "retired", "revoked"] | None = None
    attestation_issued_at: datetime | None = None
    trust_failure_reason: str | None = None
    effective_status: ProviderTrustStatus | None = None
    federation_conflict: bool = False
    federation_source_count: int = 0
    federation_sources: list[dict] = []
    federation_failure_reason: str | None = None


class TrustRegistryEntryResponse(BaseModel):
    provider_id: str
    provider_name: str
    status: ProviderTrustStatus
    trusted: bool
    latest_decision_id: str | None = None
    latest_decision_at: datetime | None = None
    trust_attestation_id: str | None = None
    trust_attestation_valid: bool = False
    registry_authority_id: str | None = None
    registry_authority_trusted: bool = False
    authority_key_id: str | None = None
    authority_key_status: Literal["active", "retired", "revoked"] | None = None
    effective_status: ProviderTrustStatus | None = None
    federation_conflict: bool = False
    federation_source_count: int = 0
    federation_sources: list[dict] = []
    federation_failure_reason: str | None = None


class ProviderApplicationRequest(BaseModel):
    provider_id: str = Field(
        min_length=1,
        max_length=100,
    )
    provider_name: str = Field(
        min_length=1,
        max_length=200,
    )
    contact_reference: str = Field(
        min_length=1,
        max_length=500,
        description=(
            "Private onboarding contact reference. This value is not returned "
            "through public trust-registry responses."
        ),
    )


class ProviderApplicationResponse(BaseModel):
    application_id: str
    provider_id: str
    provider_name: str
    application_status: ProviderApplicationStatus
    trust_status: ProviderTrustStatus
    submitted_at: datetime


class ProviderSummaryResponse(BaseModel):
    provider_id: str
    provider_name: str
    active_key_id: str
    published_key_count: int
    trust_status: ProviderTrustStatus
    provider_trusted: bool
