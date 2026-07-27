from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TransparencyLogPublishedKey(BaseModel):
    model_config = ConfigDict(frozen=True)
    key_id: str
    algorithm: Literal["Ed25519"] = "Ed25519"
    public_key: str
    status: Literal["active", "retired", "revoked"]
    created_at: datetime
    retired_at: datetime | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = None


class TransparencyLogIdentityDocument(BaseModel):
    model_config = ConfigDict(frozen=True)
    gap_version: Literal["0.12.0"] = "0.12.0"
    log_id: str
    log_name: str
    active_key_id: str
    signature_algorithm: Literal["Ed25519"] = "Ed25519"
    hash_algorithm: Literal["SHA-256"] = "SHA-256"
    tree_algorithm: Literal["GAP-RFC6962-SHA256-v1"] = "GAP-RFC6962-SHA256-v1"
    signing_keys: tuple[TransparencyLogPublishedKey, ...]
