from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TransparencyWitnessPublishedKey(BaseModel):
    model_config = ConfigDict(frozen=True)
    key_id: str
    algorithm: Literal["Ed25519"] = "Ed25519"
    public_key: str
    status: Literal["active", "retired", "revoked"]
    created_at: datetime
    retired_at: datetime | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = None


class TransparencyWitnessIdentityDocument(BaseModel):
    model_config = ConfigDict(frozen=True)
    gap_version: Literal["0.13.0"] = "0.13.0"
    witness_id: str
    witness_name: str
    active_key_id: str
    supported_statement_version: Literal["0.13.0"] = "0.13.0"
    supported_log_hash_algorithm: Literal["SHA-256"] = "SHA-256"
    signing_keys: tuple[TransparencyWitnessPublishedKey, ...]
