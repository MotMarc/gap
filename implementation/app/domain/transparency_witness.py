from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


TransparencyWitnessKeyStatus = Literal["active", "retired", "revoked"]


@dataclass(frozen=True, slots=True)
class TransparencyWitnessSigningKey:
    key_id: str
    status: TransparencyWitnessKeyStatus
    public_key_path: Path
    created_at: datetime
    private_key_path: Path | None = None
    retired_at: datetime | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.key_id.strip():
            raise ValueError("Transparency witness key IDs cannot be empty.")
        if self.created_at.tzinfo is None:
            raise ValueError("Witness key timestamps must be timezone-aware.")
        if self.status == "active":
            if self.private_key_path is None:
                raise ValueError("Active witness keys require private key material.")
            if self.retired_at is not None or self.revoked_at is not None:
                raise ValueError("Active witness keys cannot be retired or revoked.")
        elif self.status == "retired":
            if self.retired_at is None or self.revoked_at is not None:
                raise ValueError("Retired witness keys require only retired_at.")
        elif self.status == "revoked":
            if self.revoked_at is None or not self.revocation_reason:
                raise ValueError("Revoked witness keys require a time and reason.")
        else:
            raise ValueError("Unknown transparency witness key status.")
        if self.status != "revoked" and self.revocation_reason is not None:
            raise ValueError("Only revoked witness keys may declare a reason.")

    @property
    def can_sign_statements(self) -> bool:
        return self.status == "active" and self.private_key_path is not None


@dataclass(frozen=True, slots=True)
class TransparencyWitness:
    witness_id: str
    witness_name: str
    active_key_id: str
    signing_keys: tuple[TransparencyWitnessSigningKey, ...]

    def __post_init__(self) -> None:
        if not self.witness_id.strip() or not self.witness_name.strip():
            raise ValueError("Witness ID and name cannot be empty.")
        ids = [key.key_id for key in self.signing_keys]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Witness key IDs must be present and unique.")
        active = [key for key in self.signing_keys if key.status == "active"]
        if len(active) != 1 or active[0].key_id != self.active_key_id:
            raise ValueError("Witnesses must identify exactly one active key.")
        if not active[0].can_sign_statements:
            raise ValueError("The active witness key cannot sign statements.")

    @property
    def active_signing_key(self) -> TransparencyWitnessSigningKey:
        return self.get_signing_key(self.active_key_id)

    def get_signing_key(self, key_id: str) -> TransparencyWitnessSigningKey:
        key = next((item for item in self.signing_keys if item.key_id == key_id), None)
        if key is None:
            raise LookupError(f"Unknown witness key: {key_id}")
        return key
