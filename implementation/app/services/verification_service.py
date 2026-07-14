from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.crypto.canonical_json import canonicalise_model
from app.crypto.signatures import verify_payload
from app.schemas.generation_credential import GenerationCredential


def verify_generation_credential(
    credential: GenerationCredential,
    public_key: Ed25519PublicKey,
) -> bool:
    """
    Verify a Generation Credential using a provider public key.
    """

    if credential.proof.type != "Ed25519":
        return False

    canonical_payload = canonicalise_model(
        credential.payload,
    )

    return verify_payload(
        payload=canonical_payload,
        signature=credential.proof.signature,
        public_key=public_key,
    )
