from binascii import Error as Base64DecodeError
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.crypto.canonical_json import canonicalise_model
from app.crypto.provider_keys import decode_public_key, load_private_key
from app.crypto.signatures import sign_payload, verify_payload
from app.domain.provider_trust import ProviderTrustDecision
from app.domain.registry_authority import RegistryAuthorityKeyStatus
from app.schemas.registry_authority import RegistryAuthorityIdentityDocument
from app.schemas.trust_attestation import (
    TrustAttestationPayload,
    TrustAttestationProof,
    TrustDecisionAttestation,
)
from app.services.registry_authority_identity_service import (
    create_registry_authority_identity_document,
)
from app.services.registry_authority_repository import (
    RegistryAuthorityNotFoundError,
    RegistryAuthorityRepository,
)


@dataclass(frozen=True, slots=True)
class TrustAttestationVerificationResult:
    valid: bool
    authority_id: str
    key_id: str
    key_status: RegistryAuthorityKeyStatus | None
    failure_reason: str | None = None


def issue_trust_decision_attestation(
    decision: ProviderTrustDecision,
    registry_authority,
    issued_at: datetime | None = None,
    attestation_id: str | None = None,
) -> TrustDecisionAttestation:
    issue_time = issued_at or datetime.now(timezone.utc)
    if issue_time.tzinfo is None:
        raise ValueError("Trust attestation timestamps must be timezone-aware.")
    if issue_time < decision.decided_at:
        raise ValueError("A trust attestation cannot predate its decision.")
    key = registry_authority.active_signing_key
    if not key.can_sign_attestations or key.private_key_path is None:
        raise ValueError("The registry authority active private key is unavailable.")
    payload = TrustAttestationPayload(
        attestation_id=attestation_id or f"ta_{uuid4().hex}",
        decision_id=decision.decision_id,
        provider_id=decision.provider_id,
        status=decision.status,
        decision_authority=decision.authority,
        reason=decision.reason,
        decided_at=decision.decided_at,
        registry_authority_id=registry_authority.authority_id,
        registry_authority_name=registry_authority.authority_name,
        issued_at=issue_time,
    )
    signature = sign_payload(
        canonicalise_model(payload), load_private_key(key.private_key_path)
    )
    return TrustDecisionAttestation(
        payload=payload,
        proof=TrustAttestationProof(key_id=key.key_id, signature=signature),
    )


def verify_trust_attestation_details(
    attestation: TrustDecisionAttestation,
    authority_repository: RegistryAuthorityRepository,
    authority_document: RegistryAuthorityIdentityDocument | None = None,
) -> TrustAttestationVerificationResult:
    authority_id = attestation.payload.registry_authority_id
    key_id = attestation.proof.key_id
    try:
        authority = authority_repository.get(authority_id)
    except RegistryAuthorityNotFoundError:
        return TrustAttestationVerificationResult(
            False, authority_id, key_id, None, "unknown-registry-authority"
        )
    if authority_document is None:
        authority_document = create_registry_authority_identity_document(authority)
    if (
        authority_document.authority_id != authority_id
        or authority_document.authority_name
        != attestation.payload.registry_authority_name
    ):
        return TrustAttestationVerificationResult(
            False, authority_id, key_id, None, "authority-mismatch"
        )
    key = next(
        (item for item in authority_document.keys if item.key_id == key_id), None
    )
    if key is None:
        return TrustAttestationVerificationResult(
            False, authority_id, key_id, None, "unknown-authority-key"
        )
    if attestation.proof.type != key.algorithm:
        return TrustAttestationVerificationResult(
            False, authority_id, key_id, key.status, "authority-algorithm-mismatch"
        )
    if key.status == "revoked":
        return TrustAttestationVerificationResult(
            False, authority_id, key_id, key.status, "revoked-authority-key"
        )
    try:
        public_key = decode_public_key(key.public_key)
    except (ValueError, Base64DecodeError):
        return TrustAttestationVerificationResult(
            False, authority_id, key_id, key.status, "invalid-authority-public-key"
        )
    if not verify_payload(
        canonicalise_model(attestation.payload), attestation.proof.signature, public_key
    ):
        return TrustAttestationVerificationResult(
            False, authority_id, key_id, key.status, "invalid-attestation-signature"
        )
    return TrustAttestationVerificationResult(True, authority_id, key_id, key.status)
