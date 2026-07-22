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

KEY_PAIRS = {
    "gap-demo-provider retired demo-key-2026-01": (
        KEY_DIRECTORY / "provider_private.key",
        KEY_DIRECTORY / "provider_public.key",
    ),
    "gap-demo-provider active demo-key-2026-02": (
        KEY_DIRECTORY / "demo_2026_02_private.key",
        KEY_DIRECTORY / "demo_2026_02_public.key",
    ),
    "aurora-ai retired aurora-key-2026-01": (
        KEY_DIRECTORY / "aurora_private.key",
        KEY_DIRECTORY / "aurora_public.key",
    ),
    "aurora-ai active aurora-key-2026-02": (
        KEY_DIRECTORY / "aurora_2026_02_private.key",
        KEY_DIRECTORY / "aurora_2026_02_public.key",
    ),
    "meridian-ai retired meridian-key-2026-01": (
        KEY_DIRECTORY / "meridian_private.key",
        KEY_DIRECTORY / "meridian_public.key",
    ),
    "meridian-ai active meridian-key-2026-02": (
        KEY_DIRECTORY / "meridian_2026_02_private.key",
        KEY_DIRECTORY / "meridian_2026_02_public.key",
    ),
}

PUBLIC_ONLY_KEYS = {
    "gap-demo-provider revoked demo-key-2025-compromised": (
        KEY_DIRECTORY / "demo_compromised_public.key"
    ),
}


def generate_missing_key_pair(
    label: str,
    private_key_path: Path,
    public_key_path: Path,
) -> None:
    private_exists = private_key_path.exists()
    public_exists = public_key_path.exists()

    if private_exists and public_exists:
        print(f"Key pair already exists for {label}; skipping.")
        return

    if private_exists != public_exists:
        raise RuntimeError(
            f"Incomplete key pair for {label}. Delete the remaining key "
            "manually before regenerating it."
        )

    private_key, public_key = generate_provider_key_pair()

    save_private_key(private_key, private_key_path)
    save_public_key(public_key, public_key_path)

    print(f"Private key created for {label}: {private_key_path}")
    print(f"Public key created for {label}: {public_key_path}")


def generate_missing_public_only_key(
    label: str,
    public_key_path: Path,
) -> None:
    if public_key_path.exists():
        print(f"Public key already exists for {label}; skipping.")
        return

    _, public_key = generate_provider_key_pair()
    save_public_key(public_key, public_key_path)

    print(f"Public-only revoked key created for {label}: {public_key_path}")


def main() -> None:
    for label, key_paths in KEY_PAIRS.items():
        private_key_path, public_key_path = key_paths

        generate_missing_key_pair(
            label=label,
            private_key_path=private_key_path,
            public_key_path=public_key_path,
        )

    for label, public_key_path in PUBLIC_ONLY_KEYS.items():
        generate_missing_public_only_key(
            label=label,
            public_key_path=public_key_path,
        )


if __name__ == "__main__":
    main()
