from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.signed_tree_head import SignedTreeHead
from app.schemas.transparency_proof import ConsistencyProof
from app.schemas.witness_statement import WitnessStatement


class CheckpointGossipPackage(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: Literal["0.13.0"] = "0.13.0"
    gossip_id: str = Field(min_length=1, max_length=200)
    exported_at: datetime
    signed_tree_head: SignedTreeHead
    witness_statements: tuple[WitnessStatement, ...] = Field(max_length=100)
    consistency_proof_to_previous: ConsistencyProof | None = None
    previous_signed_tree_head: SignedTreeHead | None = None

    @field_validator("exported_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Gossip export timestamps must be timezone-aware.")
        return value


class GossipMonitorResult(BaseModel):
    checkpoint_gossip_consistent: bool
    split_view_detected: bool = False
    witness_equivocation_detected: bool = False
    rollback_detected: bool = False
    consistency_proven: bool = False
    consistency_unproven: bool = False
    log_id: str | None = None
    tree_head_id: str | None = None
    tree_size: int | None = None
    root_hash: str | None = None
    failure_reason: str | None = None
    conflicting_tree_head_ids: list[str] = []
    equivocating_witness_ids: list[str] = []
