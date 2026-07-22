from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProviderVerificationKey(BaseModel):
    key_id: str = Field(
        min_length=1,
        max_length=100,
    )

    algorithm: Literal["Ed25519"] = "Ed25519"

    public_key: str = Field(
        min_length=1,
    )

    status: Literal["active", "retired", "revoked"] = "active"
    created_at: datetime
    retired_at: datetime | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = Field(
        default=None,
        max_length=500,
    )


class ProviderIdentityDocument(BaseModel):
    gap_version: str = "0.0.1"

    provider_id: str = Field(
        min_length=1,
        max_length=100,
    )

    provider_name: str = Field(
        min_length=1,
        max_length=200,
    )

    active_key_id: str = Field(
        min_length=1,
        max_length=100,
    )

    keys: list[ProviderVerificationKey] = Field(
        min_length=1,
    )
