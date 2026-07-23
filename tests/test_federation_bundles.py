import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"
sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.core.registry_authority_config import (  # noqa: E402
    REFERENCE_REGISTRY_AUTHORITY,
    registry_authority_repository,
)
from app.core.repositories import trust_attestation_repository  # noqa: E402
from app.services.federation_bundle_repository import (  # noqa: E402
    FederationBundleRepository,
)
from app.services.federation_bundle_service import (  # noqa: E402
    calculate_bundle_digest,
    import_federation_bundle,
    issue_federation_bundle,
    verify_federation_bundle,
)


NOW = datetime(2026, 7, 23, 12, tzinfo=timezone.utc)


def issue(sequence=1, previous=None, bundle_id="test-bundle-1"):
    attestations = {}
    for item in trust_attestation_repository.list_all():
        attestations[item.payload.provider_id] = item
    return issue_federation_bundle(
        REFERENCE_REGISTRY_AUTHORITY,
        reversed(list(attestations.values())),
        sequence,
        NOW,
        NOW + timedelta(days=7),
        calculate_bundle_digest(previous) if previous else None,
        bundle_id,
    )


def test_valid_first_bundle_and_deterministic_ordering() -> None:
    bundle = issue()
    assert [item.payload.provider_id for item in bundle.payload.attestations] == sorted(
        item.payload.provider_id for item in bundle.payload.attestations
    )
    result = verify_federation_bundle(bundle, registry_authority_repository, now=NOW)
    assert result.valid is True
    assert result.attestation_count == result.valid_attestation_count == 3


def test_bundle_digest_is_deterministic() -> None:
    bundle = issue()
    assert calculate_bundle_digest(bundle) == calculate_bundle_digest(
        bundle.model_copy(deep=True)
    )
    assert len(calculate_bundle_digest(bundle)) == 64


@pytest.mark.parametrize(
    "field,value",
    [
        ("bundle_id", "tampered"),
        ("sequence_number", 2),
        ("expires_at", NOW + timedelta(days=8)),
    ],
)
def test_signed_payload_tampering_fails(field, value) -> None:
    bundle = issue()
    payload = bundle.payload.model_copy(update={field: value})
    tampered = bundle.model_copy(update={"payload": payload})
    result = verify_federation_bundle(tampered, registry_authority_repository, now=NOW)
    assert result.valid is False
    assert result.failure_reason == "invalid-bundle-signature"


def test_malformed_signature_fails_cleanly() -> None:
    bundle = issue()
    proof = bundle.proof.model_copy(update={"signature": "not-base64!"})
    result = verify_federation_bundle(
        bundle.model_copy(update={"proof": proof}),
        registry_authority_repository,
        now=NOW,
    )
    assert result.failure_reason == "invalid-bundle-signature"


def test_expired_future_and_long_lived_bundles_fail() -> None:
    expired = issue()
    assert (
        verify_federation_bundle(
            expired, registry_authority_repository, now=NOW + timedelta(days=8)
        ).failure_reason
        == "bundle-expired"
    )
    future = issue_federation_bundle(
        REFERENCE_REGISTRY_AUTHORITY,
        expired.payload.attestations,
        1,
        NOW + timedelta(minutes=6),
        NOW + timedelta(days=1),
        bundle_id="future",
    )
    assert (
        verify_federation_bundle(
            future, registry_authority_repository, now=NOW
        ).failure_reason
        == "bundle-not-yet-valid"
    )
    long = issue_federation_bundle(
        REFERENCE_REGISTRY_AUTHORITY,
        expired.payload.attestations,
        1,
        NOW,
        NOW + timedelta(days=31),
        bundle_id="long",
    )
    assert (
        verify_federation_bundle(
            long, registry_authority_repository, now=NOW
        ).failure_reason
        == "bundle-lifetime-too-long"
    )


def test_sequence_chain_replay_rollback_and_atomicity() -> None:
    repository = FederationBundleRepository()
    first = issue()
    assert import_federation_bundle(
        first, registry_authority_repository, repository, NOW
    ).imported
    assert not import_federation_bundle(
        first, registry_authority_repository, repository, NOW
    ).imported
    gap = issue(3, first, "gap")
    gap_result = import_federation_bundle(
        gap, registry_authority_repository, repository, NOW
    )
    assert gap_result.verification.failure_reason == "invalid-sequence"
    assert len(repository.list_all()) == 1
    second = issue(2, first, "test-bundle-2")
    assert import_federation_bundle(
        second, registry_authority_repository, repository, NOW
    ).imported
    rollback = issue(1, None, "rollback")
    assert (
        import_federation_bundle(
            rollback, registry_authority_repository, repository, NOW
        ).verification.failure_reason
        == "rollback-detected"
    )


def test_missing_predecessor_and_wrong_hash_fail() -> None:
    repository = FederationBundleRepository()
    first = issue()
    later = issue(2, first, "later")
    assert (
        verify_federation_bundle(
            later, registry_authority_repository, repository, NOW
        ).failure_reason
        == "missing-predecessor"
    )
    repository.add_verified(first)
    payload = later.payload.model_copy(update={"previous_bundle_hash": "0" * 64})
    wrong = later.model_copy(update={"payload": payload})
    # Re-signing is intentionally not available to an importer; payload tampering
    # is rejected before chain state is considered.
    assert (
        verify_federation_bundle(
            wrong, registry_authority_repository, repository, NOW
        ).failure_reason
        == "invalid-bundle-signature"
    )


def test_repository_returns_immutable_copies() -> None:
    repository = FederationBundleRepository()
    bundle = issue()
    repository.add_verified(bundle)
    assert repository.get(bundle.payload.bundle_id) == bundle
    assert repository.get(bundle.payload.bundle_id) is not bundle
