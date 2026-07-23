import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# ruff: noqa: E402

IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"
sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.crypto.provider_keys import (
    generate_provider_key_pair,
    save_private_key,
    save_public_key,
)  # noqa: E402
from app.domain.provider_trust import ProviderTrustDecision  # noqa: E402
from app.domain.registry_authority import RegistryAuthority, RegistryAuthoritySigningKey  # noqa: E402
from app.services.registry_authority_identity_service import (
    create_registry_authority_identity_document,
)  # noqa: E402
from app.services.registry_authority_repository import RegistryAuthorityRepository  # noqa: E402
from app.services.provider_application_repository import ProviderApplicationRepository  # noqa: E402
from app.services.trust_registry_repository import TrustRegistryRepository  # noqa: E402
from app.services.trust_registry_service import TrustRegistryService  # noqa: E402
from app.services.trust_attestation_repository import (
    DuplicateTrustAttestationError,
    TrustAttestationRepository,
)  # noqa: E402
from app.services.trust_attestation_service import (
    issue_trust_decision_attestation,
    verify_trust_attestation_details,
)  # noqa: E402


NOW = datetime(2026, 7, 23, tzinfo=timezone.utc)


def make_authority(tmp_path: Path, status: str = "active") -> RegistryAuthority:
    private, public = generate_provider_key_pair()
    private_path = tmp_path / "private.key"
    public_path = tmp_path / "public.key"
    save_private_key(private, private_path)
    save_public_key(public, public_path)
    kwargs = {}
    if status == "retired":
        kwargs["retired_at"] = NOW + timedelta(days=2)
    if status == "revoked":
        kwargs.update(
            revoked_at=NOW + timedelta(days=2), revocation_reason="compromised"
        )
    key = RegistryAuthoritySigningKey(
        key_id="authority-key",
        status=status,
        public_key_path=public_path,
        private_key_path=private_path if status == "active" else None,
        created_at=NOW - timedelta(days=1),
        **kwargs,
    )
    if status == "active":
        keys = (key,)
        active_key_id = key.key_id
    else:
        active_private, active_public = generate_provider_key_pair()
        active_private_path = tmp_path / "active-private.key"
        active_public_path = tmp_path / "active-public.key"
        save_private_key(active_private, active_private_path)
        save_public_key(active_public, active_public_path)
        active = RegistryAuthoritySigningKey(
            key_id="active-key",
            status="active",
            public_key_path=active_public_path,
            private_key_path=active_private_path,
            created_at=NOW,
        )
        keys = (key, active)
        active_key_id = active.key_id
    return RegistryAuthority("authority", "Test Authority", active_key_id, keys)


def decision() -> ProviderTrustDecision:
    return ProviderTrustDecision(
        "decision", "provider", "approved", "Review Board", "Approved", NOW
    )


def test_authority_requires_one_active_key(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    with pytest.raises(ValueError):
        RegistryAuthority("bad", "Bad", "authority-key", authority.signing_keys * 2)


def test_duplicate_key_ids_fail(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    with pytest.raises(ValueError, match="unique"):
        RegistryAuthority("bad", "Bad", "authority-key", authority.signing_keys * 2)


def test_attestation_signs_and_verifies(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    attestation = issue_trust_decision_attestation(decision(), authority, NOW)
    result = verify_trust_attestation_details(
        attestation, RegistryAuthorityRepository([authority])
    )
    assert result.valid is True
    assert result.key_status == "active"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider_id", "tampered"),
        ("status", "suspended"),
        ("decision_id", "other"),
        ("reason", "Changed"),
    ],
)
def test_tampered_payload_fails(tmp_path: Path, field: str, value: str) -> None:
    authority = make_authority(tmp_path)
    attestation = issue_trust_decision_attestation(decision(), authority, NOW)
    setattr(attestation.payload, field, value)
    result = verify_trust_attestation_details(
        attestation, RegistryAuthorityRepository([authority])
    )
    assert result.failure_reason == "invalid-attestation-signature"


def test_unknown_authority_fails(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    result = verify_trust_attestation_details(
        issue_trust_decision_attestation(decision(), authority, NOW),
        RegistryAuthorityRepository(),
    )
    assert result.failure_reason == "unknown-registry-authority"


def test_wrong_identity_document_fails(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    attestation = issue_trust_decision_attestation(decision(), authority, NOW)
    document = create_registry_authority_identity_document(authority)
    document.authority_name = "Wrong"
    result = verify_trust_attestation_details(
        attestation, RegistryAuthorityRepository([authority]), document
    )
    assert result.failure_reason == "authority-mismatch"


def test_unknown_key_and_algorithm_fail(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    attestation = issue_trust_decision_attestation(decision(), authority, NOW)
    attestation.proof.key_id = "unknown"
    assert (
        verify_trust_attestation_details(
            attestation, RegistryAuthorityRepository([authority])
        ).failure_reason
        == "unknown-authority-key"
    )
    attestation.proof.key_id = "authority-key"
    attestation.proof.type = "Other"
    assert (
        verify_trust_attestation_details(
            attestation, RegistryAuthorityRepository([authority])
        ).failure_reason
        == "authority-algorithm-mismatch"
    )


def test_malformed_key_and_signature_fail_cleanly(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    attestation = issue_trust_decision_attestation(decision(), authority, NOW)
    document = create_registry_authority_identity_document(authority)
    document.keys[0].public_key = "!"
    assert (
        verify_trust_attestation_details(
            attestation, RegistryAuthorityRepository([authority]), document
        ).failure_reason
        == "invalid-authority-public-key"
    )
    attestation.proof.signature = "!"
    assert (
        verify_trust_attestation_details(
            attestation, RegistryAuthorityRepository([authority])
        ).failure_reason
        == "invalid-attestation-signature"
    )


def test_attestation_cannot_predate_decision(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="predate"):
        issue_trust_decision_attestation(
            decision(), make_authority(tmp_path), NOW - timedelta(seconds=1)
        )


def test_duplicate_attestation_and_decision_binding_fail(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    attestation = issue_trust_decision_attestation(decision(), authority, NOW, "one")
    repository = TrustAttestationRepository([attestation])
    with pytest.raises(DuplicateTrustAttestationError):
        repository.add(attestation)
    second = issue_trust_decision_attestation(decision(), authority, NOW, "two")
    with pytest.raises(DuplicateTrustAttestationError):
        repository.add(second)


def test_retired_key_verifies_and_revoked_key_rejects(tmp_path: Path) -> None:
    original = make_authority(tmp_path)
    attestation = issue_trust_decision_attestation(decision(), original, NOW)
    original_key = original.signing_keys[0]
    retired = replace(
        original_key, status="retired", private_key_path=None, retired_at=NOW
    )
    active_authority = make_authority(tmp_path / "next")
    active = replace(active_authority.signing_keys[0], key_id="next")
    rotated = RegistryAuthority(
        "authority", "Test Authority", "next", (retired, active)
    )
    assert verify_trust_attestation_details(
        attestation, RegistryAuthorityRepository([rotated])
    ).valid
    revoked = replace(
        original_key,
        status="revoked",
        private_key_path=None,
        revoked_at=NOW,
        revocation_reason="compromised",
    )
    rotated = RegistryAuthority(
        "authority", "Test Authority", "next", (revoked, active)
    )
    assert (
        verify_trust_attestation_details(
            attestation, RegistryAuthorityRepository([rotated])
        ).failure_reason
        == "revoked-authority-key"
    )


def test_configured_registry_service_signs_and_evaluates_every_decision(
    tmp_path: Path,
) -> None:
    authority = make_authority(tmp_path)
    attestations = TrustAttestationRepository()
    service = TrustRegistryService(
        TrustRegistryRepository(),
        ProviderApplicationRepository(),
        RegistryAuthorityRepository([authority]),
        attestations,
        "authority",
    )
    service.record_decision("provider", "applicant", "Board", "Applied", decided_at=NOW)
    service.record_decision(
        "provider",
        "approved",
        "Board",
        "Approved",
        decided_at=NOW + timedelta(seconds=1),
    )
    assert len(attestations.list_for_provider("provider")) == 2
    evaluation = service.evaluate_provider_trust("provider")
    assert evaluation.trusted is True
    assert evaluation.attestation_valid is True
    assert evaluation.registry_authority_trusted is True


def test_approved_unsigned_decision_is_not_trusted() -> None:
    decisions = TrustRegistryRepository(
        [
            ProviderTrustDecision(
                "approved", "provider", "approved", "Board", "Approved", NOW
            )
        ]
    )
    service = TrustRegistryService(
        decisions,
        ProviderApplicationRepository(),
        RegistryAuthorityRepository(),
        TrustAttestationRepository(),
    )
    evaluation = service.evaluate_provider_trust("provider")
    assert evaluation.trusted is False
    assert evaluation.trust_failure_reason == "missing-trust-attestation"


def test_valid_attestation_from_unknown_authority_is_not_trusted(
    tmp_path: Path,
) -> None:
    authority = make_authority(tmp_path)
    trust_decision = decision()
    attestations = TrustAttestationRepository(
        [issue_trust_decision_attestation(trust_decision, authority, NOW)]
    )
    service = TrustRegistryService(
        TrustRegistryRepository([trust_decision]),
        ProviderApplicationRepository(),
        RegistryAuthorityRepository(),
        attestations,
    )
    evaluation = service.evaluate_provider_trust("provider")
    assert evaluation.trusted is False
    assert evaluation.registry_authority_trusted is False
    assert evaluation.trust_failure_reason == "unknown-registry-authority"
