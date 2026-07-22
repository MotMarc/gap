from pathlib import Path

from app.domain.provider import Provider
from app.services.provider_repository import ProviderRepository


IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[2]
KEY_DIRECTORY = IMPLEMENTATION_ROOT / "keys"


DEMO_PROVIDER = Provider(
    provider_id="gap-demo-provider",
    provider_name="GAP Demo Provider",
    key_id="demo-key-2026-01",
    private_key_path=KEY_DIRECTORY / "provider_private.key",
    public_key_path=KEY_DIRECTORY / "provider_public.key",
)

AURORA_PROVIDER = Provider(
    provider_id="aurora-ai",
    provider_name="Aurora AI",
    key_id="aurora-key-2026-01",
    private_key_path=KEY_DIRECTORY / "aurora_private.key",
    public_key_path=KEY_DIRECTORY / "aurora_public.key",
)

MERIDIAN_PROVIDER = Provider(
    provider_id="meridian-ai",
    provider_name="Meridian AI",
    key_id="meridian-key-2026-01",
    private_key_path=KEY_DIRECTORY / "meridian_private.key",
    public_key_path=KEY_DIRECTORY / "meridian_public.key",
)


PROVIDERS = [
    DEMO_PROVIDER,
    AURORA_PROVIDER,
    MERIDIAN_PROVIDER,
]


provider_repository = ProviderRepository(
    providers=PROVIDERS,
)
