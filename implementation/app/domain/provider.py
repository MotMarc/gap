from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


ProviderKeyStatus = Literal["active", "retired", "revoked"]


@dataclass(frozen=True, slots=True)
class ProviderSigningKey:
    """
    Represents one provider signing key throughout its lifecycle.

    Active keys may issue new credentials. Retired keys remain published so
    historical credentials can still be verified. Revoked keys remain
    published so verifiers can explicitly reject credentials that reference
    them.
    """

    key_id: str
    status: ProviderKeyStatus
    public_key_path: Path
    created_at: datetime
    private_key_path: Path | None = None
    retired_at: datetime | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.key_id.strip():
            raise ValueError("Provider signing key IDs cannot be empty.")

        if self.created_at.tzinfo is None:
            raise ValueError("Provider signing key timestamps must be timezone-aware.")

        if self.status == "active":
            if self.private_key_path is None:
                raise ValueError("Active provider keys require a private key path.")

            if self.retired_at is not None or self.revoked_at is not None:
                raise ValueError("Active provider keys cannot be retired or revoked.")

        if self.status == "retired":
            if self.retired_at is None:
                raise ValueError("Retired provider keys require retired_at.")

            if self.revoked_at is not None:
                raise ValueError("Retired provider keys cannot also be revoked.")

        if self.status == "revoked":
            if self.revoked_at is None:
                raise ValueError("Revoked provider keys require revoked_at.")

            if not self.revocation_reason:
                raise ValueError("Revoked provider keys require a revocation reason.")

        if self.status != "revoked" and self.revocation_reason is not None:
            raise ValueError(
                "Only revoked provider keys may declare a revocation reason."
            )

    @property
    def can_issue_credentials(self) -> bool:
        return self.status == "active" and self.private_key_path is not None


@dataclass(frozen=True, slots=True)
class Provider:
    """
    Represents a participating GAP provider and its signing-key history.
    """

    provider_id: str
    provider_name: str
    active_key_id: str
    signing_keys: tuple[ProviderSigningKey, ...]

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("Provider IDs cannot be empty.")

        if not self.provider_name.strip():
            raise ValueError("Provider names cannot be empty.")

        if not self.signing_keys:
            raise ValueError("Providers require at least one signing key.")

        key_ids = [key.key_id for key in self.signing_keys]

        if len(key_ids) != len(set(key_ids)):
            raise ValueError(
                f"Provider signing key IDs must be unique: {self.provider_id}"
            )

        active_keys = [key for key in self.signing_keys if key.status == "active"]

        if len(active_keys) != 1:
            raise ValueError(
                f"Provider {self.provider_id} must publish exactly one active key."
            )

        if active_keys[0].key_id != self.active_key_id:
            raise ValueError(
                f"Provider {self.provider_id} active_key_id does not identify "
                "its active signing key."
            )

        if not active_keys[0].can_issue_credentials:
            raise ValueError(
                f"Provider {self.provider_id} active key cannot issue credentials."
            )

    @property
    def active_signing_key(self) -> ProviderSigningKey:
        return self.get_signing_key(self.active_key_id)

    def get_signing_key(self, key_id: str) -> ProviderSigningKey:
        matching_key = next(
            (key for key in self.signing_keys if key.key_id == key_id),
            None,
        )

        if matching_key is None:
            raise LookupError(
                f"Unknown signing key {key_id} for provider {self.provider_id}."
            )

        return matching_key
