import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_DIRECTORY = PROJECT_ROOT / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.crypto.provider_keys import (  # noqa: E402
    generate_provider_key_pair,
    save_private_key,
    save_public_key,
)


PRIVATE_KEY_PATH = IMPLEMENTATION_DIRECTORY / "keys" / "provider_private.key"
PUBLIC_KEY_PATH = IMPLEMENTATION_DIRECTORY / "keys" / "provider_public.key"


def main() -> None:
    if PRIVATE_KEY_PATH.exists() or PUBLIC_KEY_PATH.exists():
        raise RuntimeError(
            "Provider keys already exist. Delete them manually before "
            "generating a replacement key pair."
        )

    private_key, public_key = generate_provider_key_pair()

    save_private_key(private_key, PRIVATE_KEY_PATH)
    save_public_key(public_key, PUBLIC_KEY_PATH)

    print(f"Private key created: {PRIVATE_KEY_PATH}")
    print(f"Public key created: {PUBLIC_KEY_PATH}")


if __name__ == "__main__":
    main()
