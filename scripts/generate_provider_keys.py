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


KEY_DIRECTORY = IMPLEMENTATION_DIRECTORY / "keys"

PROVIDER_KEY_PATHS = {
    "gap-demo-provider": (
        KEY_DIRECTORY / "provider_private.key",
        KEY_DIRECTORY / "provider_public.key",
    ),
    "aurora-ai": (
        KEY_DIRECTORY / "aurora_private.key",
        KEY_DIRECTORY / "aurora_public.key",
    ),
    "meridian-ai": (
        KEY_DIRECTORY / "meridian_private.key",
        KEY_DIRECTORY / "meridian_public.key",
    ),
}


def generate_missing_key_pair(
    provider_id: str,
    private_key_path: Path,
    public_key_path: Path,
) -> None:
    private_exists = private_key_path.exists()
    public_exists = public_key_path.exists()

    if private_exists and public_exists:
        print(
            f"Keys already exist for {provider_id}; skipping.",
        )
        return

    if private_exists != public_exists:
        raise RuntimeError(
            f"Incomplete key pair for {provider_id}. "
            "Delete the remaining key manually before regenerating.",
        )

    private_key, public_key = generate_provider_key_pair()

    save_private_key(
        private_key,
        private_key_path,
    )
    save_public_key(
        public_key,
        public_key_path,
    )

    print(
        f"Private key created for {provider_id}: {private_key_path}",
    )
    print(
        f"Public key created for {provider_id}: {public_key_path}",
    )


def main() -> None:
    for provider_id, key_paths in PROVIDER_KEY_PATHS.items():
        private_key_path, public_key_path = key_paths

        generate_missing_key_pair(
            provider_id=provider_id,
            private_key_path=private_key_path,
            public_key_path=public_key_path,
        )


if __name__ == "__main__":
    main()
