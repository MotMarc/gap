from app.crypto.provider_keys import encode_public_key, load_public_key
from app.domain.registry_authority import RegistryAuthority
from app.schemas.registry_authority import (
    RegistryAuthorityIdentityDocument,
    RegistryAuthorityVerificationKey,
)


def create_registry_authority_identity_document(
    authority: RegistryAuthority,
) -> RegistryAuthorityIdentityDocument:
    return RegistryAuthorityIdentityDocument(
        authority_id=authority.authority_id,
        authority_name=authority.authority_name,
        active_key_id=authority.active_key_id,
        keys=[
            RegistryAuthorityVerificationKey(
                key_id=key.key_id,
                public_key=encode_public_key(load_public_key(key.public_key_path)),
                status=key.status,
                created_at=key.created_at,
                retired_at=key.retired_at,
                revoked_at=key.revoked_at,
                revocation_reason=key.revocation_reason,
            )
            for key in authority.signing_keys
        ],
    )
