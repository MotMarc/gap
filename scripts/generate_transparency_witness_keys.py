import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_DIRECTORY = PROJECT_ROOT / "implementation"
sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.crypto.provider_keys import (  # noqa: E402
    generate_provider_key_pair,
    load_private_key,
    load_public_key,
    save_private_key,
    save_public_key,
)


KEY_DIRECTORY = IMPLEMENTATION_DIRECTORY / "keys"
PRIVATE_KEY_PATH = KEY_DIRECTORY / "transparency_witness_private.key"
PUBLIC_KEY_PATH = KEY_DIRECTORY / "transparency_witness_public.key"


def ensure_transparency_witness_key_pair() -> None:
    private_exists, public_exists = PRIVATE_KEY_PATH.exists(), PUBLIC_KEY_PATH.exists()
    if private_exists != public_exists:
        raise RuntimeError("Refusing to proceed: only one witness key exists.")
    if private_exists:
        private_key, public_key = (
            load_private_key(PRIVATE_KEY_PATH),
            load_public_key(PUBLIC_KEY_PATH),
        )
        derived = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        configured = public_key.public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        if derived != configured:
            raise RuntimeError("Existing transparency witness key pair does not match.")
        print("Valid transparency witness key pair already exists; unchanged.")
        return
    private_key, public_key = generate_provider_key_pair()
    save_private_key(private_key, PRIVATE_KEY_PATH)
    save_public_key(public_key, PUBLIC_KEY_PATH)
    print("Generated transparency witness Ed25519 key pair.")


if __name__ == "__main__":
    try:
        ensure_transparency_witness_key_pair()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Transparency witness key error: {error}", file=sys.stderr)
        raise SystemExit(1)
