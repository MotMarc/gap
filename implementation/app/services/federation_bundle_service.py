import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.crypto.canonical_json import canonicalise_model
from app.crypto.provider_keys import decode_public_key, load_private_key
from app.crypto.signatures import sign_payload, verify_payload
from app.schemas.federation_bundle import (
    FederationBundle,
    FederationBundleImportResult,
    FederationBundlePayload,
    FederationBundleProof,
    FederationBundleVerificationResult,
)
from app.services.registry_authority_identity_service import (
    create_registry_authority_identity_document,
)
from app.services.registry_authority_repository import RegistryAuthorityNotFoundError
from app.services.trust_attestation_service import verify_trust_attestation_details


MAX_FUTURE_CLOCK_SKEW = timedelta(minutes=5)
MAX_BUNDLE_LIFETIME = timedelta(days=30)


def calculate_bundle_digest(bundle: FederationBundle) -> str:
    return hashlib.sha256(canonicalise_model(bundle)).hexdigest()


def issue_federation_bundle(
    authority,
    attestations,
    sequence_number: int,
    issued_at: datetime,
    expires_at: datetime,
    previous_bundle_hash: str | None = None,
    bundle_id: str | None = None,
) -> FederationBundle:
    if issued_at.tzinfo is None or expires_at.tzinfo is None:
        raise ValueError("Federation bundle timestamps must be timezone-aware.")
    key = authority.active_signing_key
    if key.status != "active" or key.private_key_path is None:
        raise ValueError("The registry authority active private key is unavailable.")
    ordered = tuple(
        sorted(
            (item.model_copy(deep=True) for item in attestations),
            key=lambda item: item.payload.provider_id,
        )
    )
    # Verify against an exact, temporary authority repository without exposing keys.
    from app.services.registry_authority_repository import RegistryAuthorityRepository

    authority_repository = RegistryAuthorityRepository([authority])
    for attestation in ordered:
        verification = verify_trust_attestation_details(
            attestation, authority_repository
        )
        if not verification.valid:
            raise ValueError(
                f"Invalid contained trust attestation: {verification.failure_reason}"
            )
    payload = FederationBundlePayload(
        bundle_id=bundle_id or f"fb_{uuid4().hex}",
        registry_authority_id=authority.authority_id,
        registry_authority_name=authority.authority_name,
        sequence_number=sequence_number,
        issued_at=issued_at,
        expires_at=expires_at,
        previous_bundle_hash=previous_bundle_hash,
        attestations=ordered,
    )
    signature = sign_payload(
        canonicalise_model(payload), load_private_key(key.private_key_path)
    )
    return FederationBundle(
        payload=payload,
        proof=FederationBundleProof(key_id=key.key_id, signature=signature),
    )


def _result(bundle, **changes) -> FederationBundleVerificationResult:
    base = dict(
        valid=False,
        bundle_id=bundle.payload.bundle_id,
        registry_authority_id=bundle.payload.registry_authority_id,
        authority_key_id=bundle.proof.key_id,
        attestation_count=len(bundle.payload.attestations),
        bundle_hash=calculate_bundle_digest(bundle),
    )
    base.update(changes)
    return FederationBundleVerificationResult(**base)


def verify_federation_bundle(
    bundle: FederationBundle,
    authority_repository,
    bundle_repository=None,
    now: datetime | None = None,
) -> FederationBundleVerificationResult:
    payload = bundle.payload
    current_time = now or datetime.now(timezone.utc)
    try:
        authority = authority_repository.get(payload.registry_authority_id)
    except RegistryAuthorityNotFoundError:
        return _result(bundle, failure_reason="unknown-registry-authority")
    document = create_registry_authority_identity_document(authority)
    if (
        document.authority_id != payload.registry_authority_id
        or document.authority_name != payload.registry_authority_name
    ):
        return _result(
            bundle, registry_authority_trusted=True, failure_reason="authority-mismatch"
        )
    key = next(
        (item for item in document.keys if item.key_id == bundle.proof.key_id), None
    )
    if key is None:
        return _result(
            bundle,
            registry_authority_trusted=True,
            failure_reason="unknown-authority-key",
        )
    common = dict(registry_authority_trusted=True, authority_key_status=key.status)
    if bundle.proof.type != key.algorithm:
        return _result(bundle, **common, failure_reason="authority-algorithm-mismatch")
    if key.status == "revoked":
        return _result(bundle, **common, failure_reason="revoked-authority-key")
    try:
        public_key = decode_public_key(key.public_key)
    except ValueError:
        return _result(bundle, **common, failure_reason="invalid-authority-public-key")
    if not verify_payload(
        canonicalise_model(payload), bundle.proof.signature, public_key
    ):
        return _result(bundle, **common, failure_reason="invalid-bundle-signature")
    signed = dict(common, signature_valid=True)
    if payload.issued_at > current_time + MAX_FUTURE_CLOCK_SKEW:
        return _result(bundle, **signed, failure_reason="bundle-not-yet-valid")
    if payload.expires_at <= current_time:
        return _result(bundle, **signed, failure_reason="bundle-expired")
    if payload.expires_at - payload.issued_at > MAX_BUNDLE_LIFETIME:
        return _result(bundle, **signed, failure_reason="bundle-lifetime-too-long")
    timed = dict(signed, time_valid=True)
    latest = (
        bundle_repository.latest_for_authority(payload.registry_authority_id)
        if bundle_repository is not None
        else None
    )
    if latest is None:
        if payload.sequence_number != 1:
            return _result(bundle, **timed, failure_reason="missing-predecessor")
        if payload.previous_bundle_hash is not None:
            return _result(bundle, **timed, failure_reason="bundle-chain-mismatch")
    else:
        expected = latest.payload.sequence_number + 1
        if (
            payload.bundle_id == latest.payload.bundle_id
            or payload.sequence_number == latest.payload.sequence_number
        ):
            return _result(bundle, **timed, failure_reason="replayed-bundle")
        if payload.sequence_number < expected:
            return _result(bundle, **timed, failure_reason="rollback-detected")
        if payload.sequence_number > expected:
            return _result(bundle, **timed, failure_reason="invalid-sequence")
        if payload.previous_bundle_hash != calculate_bundle_digest(latest):
            return _result(bundle, **timed, failure_reason="bundle-chain-mismatch")
    chained = dict(timed, sequence_valid=True, chain_valid=True)
    valid_count = 0
    for attestation in payload.attestations:
        if attestation.payload.registry_authority_id != payload.registry_authority_id:
            return _result(
                bundle,
                **chained,
                invalid_attestation_count=1,
                failure_reason="attestation-authority-mismatch",
            )
        verification = verify_trust_attestation_details(
            attestation, authority_repository
        )
        if not verification.valid:
            return _result(
                bundle,
                **chained,
                valid_attestation_count=valid_count,
                invalid_attestation_count=1,
                failure_reason="invalid-contained-attestation",
            )
        valid_count += 1
    return _result(
        bundle,
        **chained,
        valid=True,
        attestations_valid=True,
        valid_attestation_count=valid_count,
    )


def import_federation_bundle(
    bundle, authority_repository, bundle_repository, now=None
) -> FederationBundleImportResult:
    verification = verify_federation_bundle(
        bundle, authority_repository, bundle_repository, now
    )
    if not verification.valid:
        return FederationBundleImportResult(imported=False, verification=verification)
    bundle_repository.add_verified(bundle)
    return FederationBundleImportResult(imported=True, verification=verification)
