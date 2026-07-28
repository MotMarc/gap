from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.federation_bundle import FederationBundle
from app.schemas.trust_attestation import TrustDecisionAttestation


class _EntryBase(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: Literal["0.12.0", "0.13.0"] = "0.13.0"
    entry_id: str = Field(min_length=1, max_length=200)
    object_id: str = Field(min_length=1, max_length=200)
    source_authority_id: str = Field(min_length=1, max_length=200)
    object_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Transparency entry timestamps must be timezone-aware.")
        return value


class TrustAttestationLogEntry(_EntryBase):
    entry_type: Literal["trust-attestation"] = "trust-attestation"
    public_object: TrustDecisionAttestation

    @model_validator(mode="after")
    def validate_binding(self):
        if self.object_id != self.public_object.payload.attestation_id:
            raise ValueError("Transparency entry object ID mismatch.")
        if self.source_authority_id != self.public_object.payload.registry_authority_id:
            raise ValueError("Transparency entry source authority mismatch.")
        return self


class FederationBundleLogEntry(_EntryBase):
    entry_type: Literal["federation-bundle"] = "federation-bundle"
    public_object: FederationBundle

    @model_validator(mode="after")
    def validate_binding(self):
        if self.object_id != self.public_object.payload.bundle_id:
            raise ValueError("Transparency entry object ID mismatch.")
        if self.source_authority_id != self.public_object.payload.registry_authority_id:
            raise ValueError("Transparency entry source authority mismatch.")
        return self


TransparencyLogEntry = Annotated[
    TrustAttestationLogEntry | FederationBundleLogEntry,
    Field(discriminator="entry_type"),
]
