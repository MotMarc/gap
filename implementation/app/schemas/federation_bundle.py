from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.trust_attestation import TrustDecisionAttestation


class FederationBundlePayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: Literal["0.11.0"] = "0.11.0"
    bundle_id: str = Field(min_length=1, max_length=200)
    registry_authority_id: str = Field(min_length=1, max_length=200)
    registry_authority_name: str = Field(min_length=1, max_length=300)
    sequence_number: int = Field(ge=1)
    issued_at: datetime
    expires_at: datetime
    previous_bundle_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    attestations: tuple[TrustDecisionAttestation, ...] = Field(
        min_length=1, max_length=1000
    )

    @field_validator("issued_at", "expires_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Federation bundle timestamps must be timezone-aware.")
        return value

    @model_validator(mode="after")
    def validate_payload(self):
        if self.expires_at <= self.issued_at:
            raise ValueError("Federation bundle expiry must follow issuance.")
        if self.sequence_number == 1 and self.previous_bundle_hash is not None:
            raise ValueError("The first federation bundle cannot have a predecessor.")
        provider_ids = [item.payload.provider_id for item in self.attestations]
        attestation_ids = [item.payload.attestation_id for item in self.attestations]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("Federation bundles cannot contain duplicate providers.")
        if len(attestation_ids) != len(set(attestation_ids)):
            raise ValueError(
                "Federation bundles cannot contain duplicate attestations."
            )
        if any(
            item.payload.registry_authority_id != self.registry_authority_id
            for item in self.attestations
        ):
            raise ValueError(
                "Contained attestations must belong to the bundle authority."
            )
        return self


class FederationBundleProof(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["Ed25519"] = "Ed25519"
    key_id: str = Field(min_length=1, max_length=200)
    signature: str = Field(min_length=1, max_length=1000)


class FederationBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    payload: FederationBundlePayload
    proof: FederationBundleProof


class FederationBundleVerificationResult(BaseModel):
    valid: bool
    bundle_id: str | None = None
    registry_authority_id: str | None = None
    registry_authority_trusted: bool = False
    authority_key_id: str | None = None
    authority_key_status: Literal["active", "retired", "revoked"] | None = None
    signature_valid: bool = False
    time_valid: bool = False
    sequence_valid: bool = False
    chain_valid: bool = False
    attestations_valid: bool = False
    attestation_count: int = 0
    valid_attestation_count: int = 0
    invalid_attestation_count: int = 0
    bundle_hash: str | None = None
    failure_reason: str | None = None


class FederationBundleImportResult(BaseModel):
    imported: bool
    verification: FederationBundleVerificationResult
