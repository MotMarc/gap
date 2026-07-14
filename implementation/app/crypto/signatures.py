import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def sign_payload(
    payload: bytes,
    private_key: Ed25519PrivateKey,
) -> str:
    """
    Sign a canonical payload using Ed25519.

    Returns the signature encoded as Base64.
    """

    signature = private_key.sign(payload)

    return base64.b64encode(signature).decode("utf-8")


def verify_payload(
    payload: bytes,
    signature: str,
    public_key: Ed25519PublicKey,
) -> bool:
    """
    Verify a Base64 encoded Ed25519 signature.
    """

    try:
        public_key.verify(
            base64.b64decode(signature),
            payload,
        )

        return True

    except InvalidSignature:
        return False
