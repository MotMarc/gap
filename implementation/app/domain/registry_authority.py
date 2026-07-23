from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


RegistryAuthorityKeyStatus = Literal["active", "retired", "revoked"]


@dataclass(frozen=True, slots=True)
class RegistryAuthoritySigningKey:
    key_id: str
    status: RegistryAuthorityKeyStatus
    public_key_path: Path
    created_at: datetime
    private_key_path: Path | None = None
    retired_at: datetime | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.key_id.strip():
            raise ValueError("Registry authority signing key IDs cannot be empty.")
        if self.created_at.tzinfo is None:
            raise ValueError(
                "Registry authority key timestamps must be timezone-aware."
            )
        if self.status == "active":
            if self.private_key_path is None:
                raise ValueError(
                    "Active registry authority keys require a private key path."
                )
            if self.retired_at is not None or self.revoked_at is not None:
                raise ValueError(
                    "Active registry authority keys cannot be retired or revoked."
                )
        elif self.status == "retired":
            if self.retired_at is None:
                raise ValueError("Retired registry authority keys require retired_at.")
            if self.revoked_at is not None:
                raise ValueError(
                    "Retired registry authority keys cannot also be revoked."
                )
        elif self.status == "revoked":
            if self.revoked_at is None:
                raise ValueError("Revoked registry authority keys require revoked_at.")
            if not self.revocation_reason:
                raise ValueError(
                    "Revoked registry authority keys require a revocation reason."
                )
        if self.status != "revoked" and self.revocation_reason is not None:
            raise ValueError(
                "Only revoked registry authority keys may declare a reason."
            )

    @property
    def can_sign_attestations(self) -> bool:
        return self.status == "active" and self.private_key_path is not None


@dataclass(frozen=True, slots=True)
class RegistryAuthority:
    authority_id: str
    authority_name: str
    active_key_id: str
    signing_keys: tuple[RegistryAuthoritySigningKey, ...]

    def __post_init__(self) -> None:
        if not self.authority_id.strip():
            raise ValueError("Registry authority IDs cannot be empty.")
        if not self.authority_name.strip():
            raise ValueError("Registry authority names cannot be empty.")
        if not self.signing_keys:
            raise ValueError("Registry authorities require at least one signing key.")
        key_ids = [key.key_id for key in self.signing_keys]
        if len(key_ids) != len(set(key_ids)):
            raise ValueError("Registry authority signing key IDs must be unique.")
        active_keys = [key for key in self.signing_keys if key.status == "active"]
        if len(active_keys) != 1:
            raise ValueError(
                f"Registry authority {self.authority_id} must publish exactly one active key."
            )
        if active_keys[0].key_id != self.active_key_id:
            raise ValueError(
                "Registry authority active_key_id must identify its active signing key."
            )
        if not active_keys[0].can_sign_attestations:
            raise ValueError("Registry authority active key cannot sign attestations.")

    @property
    def active_signing_key(self) -> RegistryAuthoritySigningKey:
        return self.get_signing_key(self.active_key_id)

    def get_signing_key(self, key_id: str) -> RegistryAuthoritySigningKey:
        key = next((key for key in self.signing_keys if key.key_id == key_id), None)
        if key is None:
            raise LookupError(
                f"Unknown signing key {key_id} for authority {self.authority_id}."
            )
        return key
