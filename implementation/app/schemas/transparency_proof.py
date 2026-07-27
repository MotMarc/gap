from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.signed_tree_head import SignedTreeHead
from app.schemas.transparency_entry import (
    FederationBundleLogEntry,
    TrustAttestationLogEntry,
)
from app.schemas.transparency_log import TransparencyLogIdentityDocument


class InclusionProof(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: Literal["0.12.0"] = "0.12.0"
    log_id: str
    tree_size: int = Field(ge=1, le=1_000_000)
    leaf_index: int = Field(ge=0)
    entry_id: str
    leaf_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    root_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    audit_path: tuple[str, ...] = Field(max_length=64)


class ConsistencyProof(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: Literal["0.12.0"] = "0.12.0"
    log_id: str
    old_tree_size: int = Field(ge=0, le=1_000_000)
    new_tree_size: int = Field(ge=0, le=1_000_000)
    old_root_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    new_root_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    consistency_path: tuple[str, ...] = Field(max_length=64)


class InclusionVerificationRequest(BaseModel):
    entry: TrustAttestationLogEntry | FederationBundleLogEntry
    tree_head: SignedTreeHead
    proof: InclusionProof
    log_identity: TransparencyLogIdentityDocument | None = None


class InclusionVerificationResult(BaseModel):
    valid: bool
    entry_id: str | None = None
    tree_head_id: str | None = None
    failure_reason: str | None = None


class ConsistencyVerificationRequest(BaseModel):
    old_tree_head: SignedTreeHead
    new_tree_head: SignedTreeHead
    proof: ConsistencyProof


class ConsistencyVerificationResult(BaseModel):
    valid: bool
    append_only: bool = False
    split_view: bool = False
    failure_reason: str | None = None


class TreeHeadComparisonRequest(BaseModel):
    old_tree_head: SignedTreeHead
    new_tree_head: SignedTreeHead
    proof: ConsistencyProof | None = None
