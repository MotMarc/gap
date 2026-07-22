from datetime import datetime, timezone
from pathlib import Path

from app.domain.provider import Provider, ProviderSigningKey
from app.services.provider_repository import ProviderRepository


IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[2]
KEY_DIRECTORY = IMPLEMENTATION_ROOT / "keys"


DEMO_PROVIDER = Provider(
    provider_id="gap-demo-provider",
    provider_name="GAP Demo Provider",
    active_key_id="demo-key-2026-02",
    signing_keys=(
        ProviderSigningKey(
            key_id="demo-key-2026-02",
            status="active",
            created_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
            private_key_path=KEY_DIRECTORY / "demo_2026_02_private.key",
            public_key_path=KEY_DIRECTORY / "demo_2026_02_public.key",
        ),
        ProviderSigningKey(
            key_id="demo-key-2026-01",
            status="retired",
            created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
            retired_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
            private_key_path=KEY_DIRECTORY / "provider_private.key",
            public_key_path=KEY_DIRECTORY / "provider_public.key",
        ),
        ProviderSigningKey(
            key_id="demo-key-2025-compromised",
            status="revoked",
            created_at=datetime(2025, 10, 1, tzinfo=timezone.utc),
            revoked_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
            revocation_reason="Demonstration key compromise",
            public_key_path=KEY_DIRECTORY / "demo_compromised_public.key",
        ),
    ),
)

AURORA_PROVIDER = Provider(
    provider_id="aurora-ai",
    provider_name="Aurora AI",
    active_key_id="aurora-key-2026-02",
    signing_keys=(
        ProviderSigningKey(
            key_id="aurora-key-2026-02",
            status="active",
            created_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
            private_key_path=KEY_DIRECTORY / "aurora_2026_02_private.key",
            public_key_path=KEY_DIRECTORY / "aurora_2026_02_public.key",
        ),
        ProviderSigningKey(
            key_id="aurora-key-2026-01",
            status="retired",
            created_at=datetime(2026, 1, 20, tzinfo=timezone.utc),
            retired_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
            private_key_path=KEY_DIRECTORY / "aurora_private.key",
            public_key_path=KEY_DIRECTORY / "aurora_public.key",
        ),
    ),
)

MERIDIAN_PROVIDER = Provider(
    provider_id="meridian-ai",
    provider_name="Meridian AI",
    active_key_id="meridian-key-2026-02",
    signing_keys=(
        ProviderSigningKey(
            key_id="meridian-key-2026-02",
            status="active",
            created_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
            private_key_path=KEY_DIRECTORY / "meridian_2026_02_private.key",
            public_key_path=KEY_DIRECTORY / "meridian_2026_02_public.key",
        ),
        ProviderSigningKey(
            key_id="meridian-key-2026-01",
            status="retired",
            created_at=datetime(2026, 1, 25, tzinfo=timezone.utc),
            retired_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
            private_key_path=KEY_DIRECTORY / "meridian_private.key",
            public_key_path=KEY_DIRECTORY / "meridian_public.key",
        ),
    ),
)


PROVIDERS = [
    DEMO_PROVIDER,
    AURORA_PROVIDER,
    MERIDIAN_PROVIDER,
]


provider_repository = ProviderRepository(
    providers=PROVIDERS,
)
