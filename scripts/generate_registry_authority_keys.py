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
PRIVATE_KEY_PATH = KEY_DIRECTORY / "registry_authority_private.key"
PUBLIC_KEY_PATH = KEY_DIRECTORY / "registry_authority_public.key"


def ensure_registry_authority_key_pair() -> None:
    private_exists = PRIVATE_KEY_PATH.exists()
    public_exists = PUBLIC_KEY_PATH.exists()
    if private_exists != public_exists:
        raise RuntimeError(
            "Refusing to proceed: only one registry authority key file exists."
        )
    if private_exists:
        private_key = load_private_key(PRIVATE_KEY_PATH)
        public_key = load_public_key(PUBLIC_KEY_PATH)
        derived = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        configured = public_key.public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        if derived != configured:
            raise RuntimeError("Existing registry authority key pair does not match.")
        print("Valid registry authority key pair already exists; unchanged.")
        return
    private_key, public_key = generate_provider_key_pair()
    save_private_key(private_key, PRIVATE_KEY_PATH)
    save_public_key(public_key, PUBLIC_KEY_PATH)
    print("Generated registry authority Ed25519 key pair.")


if __name__ == "__main__":
    ensure_registry_authority_key_pair()
