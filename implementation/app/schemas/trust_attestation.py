from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.provider_trust import ProviderTrustStatus


class TrustAttestationPayload(BaseModel):
    version: str = "0.10.0"
    attestation_id: str
    decision_id: str
    provider_id: str
    status: ProviderTrustStatus
    decision_authority: str
    reason: str
    decided_at: datetime
    registry_authority_id: str
    registry_authority_name: str
    issued_at: datetime


class TrustAttestationProof(BaseModel):
    type: Literal["Ed25519"] = "Ed25519"
    key_id: str
    signature: str = Field(min_length=1)


class TrustDecisionAttestation(BaseModel):
    payload: TrustAttestationPayload
    proof: TrustAttestationProof
