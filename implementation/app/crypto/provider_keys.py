import base64
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


def generate_provider_key_pair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """
    Generate a new Ed25519 provider signing key pair.
    """

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    return private_key, public_key


def save_private_key(
    private_key: Ed25519PrivateKey,
    path: Path,
) -> None:
    """
    Save an Ed25519 private key as raw base64 text.
    """

    raw_private_key = private_key.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption(),
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        base64.b64encode(raw_private_key).decode("utf-8"),
        encoding="utf-8",
    )


def save_public_key(
    public_key: Ed25519PublicKey,
    path: Path,
) -> None:
    """
    Save an Ed25519 public key as raw base64 text.
    """

    raw_public_key = public_key.public_bytes(
        encoding=Encoding.Raw,
        format=PublicFormat.Raw,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        base64.b64encode(raw_public_key).decode("utf-8"),
        encoding="utf-8",
    )


def load_private_key(path: Path) -> Ed25519PrivateKey:
    encoded_key = path.read_text(encoding="utf-8")
    raw_key = base64.b64decode(encoded_key)

    return Ed25519PrivateKey.from_private_bytes(raw_key)


def load_public_key(path: Path) -> Ed25519PublicKey:
    encoded_key = path.read_text(encoding="utf-8")
    raw_key = base64.b64decode(encoded_key)

    return Ed25519PublicKey.from_public_bytes(raw_key)


def encode_public_key(
    public_key: Ed25519PublicKey,
) -> str:
    """
    Encode an Ed25519 public key as Base64 text.
    """

    raw_public_key = public_key.public_bytes(
        encoding=Encoding.Raw,
        format=PublicFormat.Raw,
    )

    return base64.b64encode(raw_public_key).decode("utf-8")


def decode_public_key(
    encoded_public_key: str,
) -> Ed25519PublicKey:
    """
    Decode a Base64 encoded Ed25519 public key.
    """

    raw_public_key = base64.b64decode(
        encoded_public_key,
        validate=True,
    )

    return Ed25519PublicKey.from_public_bytes(raw_public_key)
