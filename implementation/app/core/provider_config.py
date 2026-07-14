from pathlib import Path


IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[2]
KEY_DIRECTORY = IMPLEMENTATION_ROOT / "keys"

PRIVATE_KEY_PATH = KEY_DIRECTORY / "provider_private.key"
PUBLIC_KEY_PATH = KEY_DIRECTORY / "provider_public.key"

PROVIDER_ID = "gap-demo-provider"
PROVIDER_NAME = "GAP Demo Provider"
KEY_ID = "key-2026-01"
