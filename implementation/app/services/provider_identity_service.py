from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.crypto.provider_keys import encode_public_key
from app.schemas.provider_identity import (
    ProviderIdentityDocument,
    ProviderVerificationKey,
)


CURRENT_GAP_VERSION = "0.0.1"


def create_provider_identity_document(
    provider_id: str,
    provider_name: str,
    key_id: str,
    public_key: Ed25519PublicKey,
) -> ProviderIdentityDocument:
    """
    Create a public GAP Provider Identity Document.
    """

    return ProviderIdentityDocument(
        gap_version=CURRENT_GAP_VERSION,
        provider_id=provider_id,
        provider_name=provider_name,
        keys=[
            ProviderVerificationKey(
                key_id=key_id,
                algorithm="Ed25519",
                public_key=encode_public_key(public_key),
                status="active",
            )
        ],
    )
