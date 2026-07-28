from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WitnessStatementPayload(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: Literal["0.13.0"] = "0.13.0"
    statement_id: str = Field(min_length=1, max_length=200)
    witness_id: str = Field(min_length=1, max_length=200)
    witness_name: str = Field(min_length=1, max_length=300)
    log_id: str = Field(min_length=1, max_length=200)
    tree_head_id: str = Field(min_length=1, max_length=200)
    tree_size: int = Field(ge=0, le=1_000_000)
    root_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    tree_head_timestamp: datetime
    observed_at: datetime
    verification_outcome: Literal["accepted"] = "accepted"
    consistency_reference_tree_size: int | None = Field(default=None, ge=0)
    consistency_reference_root_hash: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )

    @field_validator("tree_head_timestamp", "observed_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Witness statement timestamps must be timezone-aware.")
        return value


class WitnessStatementProof(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["Ed25519"] = "Ed25519"
    key_id: str
    signature: str


class WitnessStatement(BaseModel):
    model_config = ConfigDict(frozen=True)
    payload: WitnessStatementPayload
    proof: WitnessStatementProof


class WitnessStatementVerificationResult(BaseModel):
    valid: bool
    statement_id: str | None = None
    witness_id: str | None = None
    witness_trusted: bool = False
    witness_key_id: str | None = None
    witness_key_status: Literal["active", "retired", "revoked"] | None = None
    log_id: str | None = None
    tree_head_id: str | None = None
    tree_size: int | None = None
    root_hash: str | None = None
    statement_signature_valid: bool = False
    checkpoint_binding_valid: bool = False
    statement_fresh: bool = False
    failure_reason: str | None = None
