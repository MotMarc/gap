from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RegistryAuthorityVerificationKey(BaseModel):
    key_id: str
    algorithm: Literal["Ed25519"] = "Ed25519"
    public_key: str
    status: Literal["active", "retired", "revoked"]
    created_at: datetime
    retired_at: datetime | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = None


class RegistryAuthorityIdentityDocument(BaseModel):
    gap_version: str = "0.10.0"
    authority_id: str
    authority_name: str
    active_key_id: str
    keys: list[RegistryAuthorityVerificationKey] = Field(min_length=1)


class RegistryAuthoritySummaryResponse(BaseModel):
    authority_id: str
    authority_name: str
    active_key_id: str
    published_key_count: int
    trusted_by_local_registry: bool
