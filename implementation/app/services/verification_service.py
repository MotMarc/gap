from binascii import Error as Base64DecodeError
from dataclasses import dataclass

from app.crypto.canonical_json import canonicalise_model
from app.crypto.provider_keys import decode_public_key
from app.crypto.signatures import verify_payload
from app.domain.provider import ProviderKeyStatus
from app.schemas.generation_credential import GenerationCredential
from app.schemas.provider_identity import ProviderIdentityDocument


@dataclass(frozen=True, slots=True)
class CredentialVerificationResult:
    valid: bool
    key_status: ProviderKeyStatus | None
    failure_reason: str | None = None


def verify_generation_credential_details(
    credential: GenerationCredential,
    provider_document: ProviderIdentityDocument,
) -> CredentialVerificationResult:
    """
    Verify a credential and return a machine-readable decision explanation.
    """

    if credential.payload.provider.provider_id != provider_document.provider_id:
        return CredentialVerificationResult(
            valid=False,
            key_status=None,
            failure_reason="provider-mismatch",
        )

    matching_key = next(
        (
            key
            for key in provider_document.keys
            if key.key_id == credential.proof.key_id
        ),
        None,
    )

    if matching_key is None:
        return CredentialVerificationResult(
            valid=False,
            key_status=None,
            failure_reason="unknown-key",
        )

    if credential.proof.type != matching_key.algorithm:
        return CredentialVerificationResult(
            valid=False,
            key_status=matching_key.status,
            failure_reason="algorithm-mismatch",
        )

    if matching_key.status == "revoked":
        return CredentialVerificationResult(
            valid=False,
            key_status=matching_key.status,
            failure_reason="revoked-key",
        )

    try:
        public_key = decode_public_key(matching_key.public_key)
    except (ValueError, Base64DecodeError):
        return CredentialVerificationResult(
            valid=False,
            key_status=matching_key.status,
            failure_reason="invalid-public-key",
        )

    canonical_payload = canonicalise_model(
        credential.payload,
    )

    signature_valid = verify_payload(
        payload=canonical_payload,
        signature=credential.proof.signature,
        public_key=public_key,
    )

    if not signature_valid:
        return CredentialVerificationResult(
            valid=False,
            key_status=matching_key.status,
            failure_reason="invalid-signature",
        )

    return CredentialVerificationResult(
        valid=True,
        key_status=matching_key.status,
    )


def verify_generation_credential(
    credential: GenerationCredential,
    provider_document: ProviderIdentityDocument,
) -> bool:
    """
    Return whether a Generation Credential is valid.

    Active and retired keys may validate credentials. Revoked keys may not.
    """

    return verify_generation_credential_details(
        credential=credential,
        provider_document=provider_document,
    ).valid
