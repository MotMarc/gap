from binascii import Error as Base64DecodeError

from app.crypto.canonical_json import canonicalise_model
from app.crypto.provider_keys import decode_public_key
from app.crypto.signatures import verify_payload
from app.schemas.generation_credential import GenerationCredential
from app.schemas.provider_identity import ProviderIdentityDocument


def verify_generation_credential(
    credential: GenerationCredential,
    provider_document: ProviderIdentityDocument,
) -> bool:
    """
    Verify a Generation Credential against a Provider Identity Document.
    """

    if credential.payload.provider.provider_id != provider_document.provider_id:
        return False

    matching_key = next(
        (
            key
            for key in provider_document.keys
            if key.key_id == credential.proof.key_id
        ),
        None,
    )

    if matching_key is None:
        return False

    if credential.proof.type != matching_key.algorithm:
        return False

    if matching_key.status == "revoked":
        return False

    try:
        public_key = decode_public_key(matching_key.public_key)
    except (ValueError, Base64DecodeError):
        return False

    canonical_payload = canonicalise_model(
        credential.payload,
    )

    return verify_payload(
        payload=canonical_payload,
        signature=credential.proof.signature,
        public_key=public_key,
    )
