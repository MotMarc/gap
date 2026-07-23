from datetime import datetime, timezone
from pathlib import Path

from app.domain.registry_authority import (
    RegistryAuthority,
    RegistryAuthoritySigningKey,
)
from app.services.registry_authority_repository import RegistryAuthorityRepository


KEY_DIRECTORY = Path(__file__).resolve().parents[2] / "keys"

REFERENCE_REGISTRY_AUTHORITY = RegistryAuthority(
    authority_id="gap-reference-registry",
    authority_name="GAP Reference Registry Authority",
    active_key_id="gap-registry-key-2026-01",
    signing_keys=(
        RegistryAuthoritySigningKey(
            key_id="gap-registry-key-2026-01",
            status="active",
            public_key_path=KEY_DIRECTORY / "registry_authority_public.key",
            private_key_path=KEY_DIRECTORY / "registry_authority_private.key",
            created_at=datetime(2026, 7, 23, tzinfo=timezone.utc),
        ),
    ),
)

registry_authority_repository = RegistryAuthorityRepository(
    [REFERENCE_REGISTRY_AUTHORITY]
)
