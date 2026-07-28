from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TreeHeadPayload(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: Literal["0.12.0", "0.13.0"] = "0.13.0"
    tree_head_id: str = Field(min_length=1, max_length=200)
    log_id: str = Field(min_length=1, max_length=200)
    log_name: str = Field(min_length=1, max_length=300)
    tree_size: int = Field(ge=0, le=1_000_000)
    root_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Tree-head timestamps must be timezone-aware.")
        return value


class TreeHeadProof(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["Ed25519"] = "Ed25519"
    key_id: str
    signature: str


class SignedTreeHead(BaseModel):
    model_config = ConfigDict(frozen=True)
    payload: TreeHeadPayload
    proof: TreeHeadProof


class TreeHeadVerificationResult(BaseModel):
    valid: bool
    tree_head_id: str | None = None
    log_id: str | None = None
    tree_size: int | None = None
    root_hash: str | None = None
    key_id: str | None = None
    key_status: Literal["active", "retired", "revoked"] | None = None
    signature_valid: bool = False
    log_trusted: bool = False
    failure_reason: str | None = None
