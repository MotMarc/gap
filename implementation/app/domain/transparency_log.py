from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


TransparencyLogKeyStatus = Literal["active", "retired", "revoked"]


@dataclass(frozen=True, slots=True)
class TransparencyLogSigningKey:
    key_id: str
    status: TransparencyLogKeyStatus
    public_key_path: Path
    created_at: datetime
    private_key_path: Path | None = None
    retired_at: datetime | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.key_id.strip():
            raise ValueError("Transparency log signing key IDs cannot be empty.")
        if self.created_at.tzinfo is None:
            raise ValueError("Transparency log key timestamps must be timezone-aware.")
        if self.status == "active":
            if self.private_key_path is None:
                raise ValueError(
                    "Active transparency log keys require a private key path."
                )
            if self.retired_at is not None or self.revoked_at is not None:
                raise ValueError(
                    "Active transparency log keys cannot be retired or revoked."
                )
        elif self.status == "retired":
            if self.retired_at is None:
                raise ValueError("Retired transparency log keys require retired_at.")
            if self.revoked_at is not None:
                raise ValueError(
                    "Retired transparency log keys cannot also be revoked."
                )
        elif self.status == "revoked":
            if self.revoked_at is None or not self.revocation_reason:
                raise ValueError(
                    "Revoked transparency log keys require revoked_at and a reason."
                )
        else:
            raise ValueError("Unknown transparency log key status.")
        if self.status != "revoked" and self.revocation_reason is not None:
            raise ValueError("Only revoked transparency log keys may declare a reason.")

    @property
    def can_sign_tree_heads(self) -> bool:
        return self.status == "active" and self.private_key_path is not None


@dataclass(frozen=True, slots=True)
class TransparencyLogOperator:
    log_id: str
    log_name: str
    active_key_id: str
    signing_keys: tuple[TransparencyLogSigningKey, ...]

    def __post_init__(self) -> None:
        if not self.log_id.strip() or not self.log_name.strip():
            raise ValueError("Transparency log ID and name cannot be empty.")
        key_ids = [key.key_id for key in self.signing_keys]
        if not key_ids:
            raise ValueError("Transparency logs require at least one signing key.")
        if len(key_ids) != len(set(key_ids)):
            raise ValueError("Transparency log signing key IDs must be unique.")
        active = [key for key in self.signing_keys if key.status == "active"]
        if len(active) != 1:
            raise ValueError("Transparency logs must publish exactly one active key.")
        if active[0].key_id != self.active_key_id:
            raise ValueError("active_key_id must identify the active log signing key.")
        if not active[0].can_sign_tree_heads:
            raise ValueError("The active transparency log key cannot sign tree heads.")

    @property
    def active_signing_key(self) -> TransparencyLogSigningKey:
        return self.get_signing_key(self.active_key_id)

    def get_signing_key(self, key_id: str) -> TransparencyLogSigningKey:
        for key in self.signing_keys:
            if key.key_id == key_id:
                return key
        raise LookupError(f"Unknown signing key {key_id} for log {self.log_id}.")
