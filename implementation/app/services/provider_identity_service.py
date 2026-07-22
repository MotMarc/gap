from app.crypto.provider_keys import encode_public_key, load_public_key
from app.domain.provider import Provider
from app.schemas.provider_identity import (
    ProviderIdentityDocument,
    ProviderVerificationKey,
)


CURRENT_GAP_VERSION = "0.0.1"


def create_provider_identity_document(
    provider: Provider,
) -> ProviderIdentityDocument:
    """
    Create a public identity document containing the provider's complete
    verification-key history.
    """

    verification_keys = []

    for signing_key in provider.signing_keys:
        public_key = load_public_key(signing_key.public_key_path)

        verification_keys.append(
            ProviderVerificationKey(
                key_id=signing_key.key_id,
                algorithm="Ed25519",
                public_key=encode_public_key(public_key),
                status=signing_key.status,
                created_at=signing_key.created_at,
                retired_at=signing_key.retired_at,
                revoked_at=signing_key.revoked_at,
                revocation_reason=signing_key.revocation_reason,
            )
        )

    return ProviderIdentityDocument(
        gap_version=CURRENT_GAP_VERSION,
        provider_id=provider.provider_id,
        provider_name=provider.provider_name,
        active_key_id=provider.active_key_id,
        keys=verification_keys,
    )
