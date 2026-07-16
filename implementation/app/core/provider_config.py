from pathlib import Path

from app.domain.provider import Provider
from app.services.provider_repository import ProviderRepository


IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[2]
KEY_DIRECTORY = IMPLEMENTATION_ROOT / "keys"

DEMO_PROVIDER = Provider(
    provider_id="gap-demo-provider",
    provider_name="GAP Demo Provider",
    key_id="key-2026-01",
    private_key_path=KEY_DIRECTORY / "provider_private.key",
    public_key_path=KEY_DIRECTORY / "provider_public.key",
)

provider_repository = ProviderRepository(
    providers=[DEMO_PROVIDER],
)
