import sys
from datetime import datetime, timezone
from pathlib import Path

IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.crypto.provider_keys import (  # noqa: E402
    encode_public_key,
    generate_provider_key_pair,
)
from app.domain.generation_event import GenerationEvent  # noqa: E402
from app.schemas.provider_identity import (  # noqa: E402
    ProviderIdentityDocument,
    ProviderVerificationKey,
)
from app.services.artifact_service import (  # noqa: E402
    create_artifact_descriptor,
)
from app.services.generation_credential_service import (  # noqa: E402
    create_credential_payload,
    issue_generation_credential,
)
from app.services.verification_service import (  # noqa: E402
    verify_generation_credential,
    verify_generation_credential_details,
)


def create_test_event() -> GenerationEvent:
    return GenerationEvent(
        generation_id="gid_" + "a" * 64,
        provider_id="gap-demo-provider",
        model_id="demo-model-v1",
        created_at=datetime.now(timezone.utc),
        gap_version="0.1",
    )


def create_test_credential_and_document(
    key_status: str = "active",
):
    private_key, public_key = generate_provider_key_pair()

    artifact = create_artifact_descriptor(
        artifact=b"generated artifact",
        media_type="text/plain",
    )

    payload = create_credential_payload(
        event=create_test_event(),
        artifacts=[artifact],
    )

    credential = issue_generation_credential(
        payload=payload,
        key_id="key-2026-01",
        private_key=private_key,
    )

    provider_document = ProviderIdentityDocument(
        provider_id="gap-demo-provider",
        provider_name="GAP Demo Provider",
        active_key_id=(
            "key-2026-01" if key_status == "active" else "different-active-key"
        ),
        keys=[
            ProviderVerificationKey(
                key_id="key-2026-01",
                public_key=encode_public_key(public_key),
                status=key_status,
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                retired_at=(
                    datetime(2026, 7, 1, tzinfo=timezone.utc)
                    if key_status == "retired"
                    else None
                ),
                revoked_at=(
                    datetime(2026, 7, 1, tzinfo=timezone.utc)
                    if key_status == "revoked"
                    else None
                ),
                revocation_reason=(
                    "Test compromise" if key_status == "revoked" else None
                ),
            )
        ],
    )

    return credential, provider_document


def test_active_key_credential_signature_is_valid() -> None:
    credential, provider_document = create_test_credential_and_document()

    result = verify_generation_credential_details(
        credential=credential,
        provider_document=provider_document,
    )

    assert result.valid is True
    assert result.key_status == "active"
    assert result.failure_reason is None


def test_retired_key_credential_remains_valid() -> None:
    credential, provider_document = create_test_credential_and_document(
        key_status="retired"
    )

    result = verify_generation_credential_details(
        credential=credential,
        provider_document=provider_document,
    )

    assert result.valid is True
    assert result.key_status == "retired"
    assert result.failure_reason is None


def test_modified_payload_fails_verification() -> None:
    credential, provider_document = create_test_credential_and_document()

    credential.payload.model.model_id = "tampered-model"

    result = verify_generation_credential_details(
        credential=credential,
        provider_document=provider_document,
    )

    assert result.valid is False
    assert result.failure_reason == "invalid-signature"


def test_unknown_key_id_fails_verification() -> None:
    credential, provider_document = create_test_credential_and_document()

    credential.proof.key_id = "unknown-key"

    result = verify_generation_credential_details(
        credential=credential,
        provider_document=provider_document,
    )

    assert result.valid is False
    assert result.key_status is None
    assert result.failure_reason == "unknown-key"


def test_wrong_provider_fails_verification() -> None:
    credential, provider_document = create_test_credential_and_document()

    provider_document.provider_id = "different-provider"

    result = verify_generation_credential_details(
        credential=credential,
        provider_document=provider_document,
    )

    assert result.valid is False
    assert result.failure_reason == "provider-mismatch"


def test_revoked_key_fails_verification() -> None:
    credential, provider_document = create_test_credential_and_document(
        key_status="revoked"
    )

    result = verify_generation_credential_details(
        credential=credential,
        provider_document=provider_document,
    )

    assert result.valid is False
    assert result.key_status == "revoked"
    assert result.failure_reason == "revoked-key"


def test_tampered_public_key_fails_verification() -> None:
    credential, provider_document = create_test_credential_and_document()

    provider_document.keys[0].public_key = "not-valid-base64"

    result = verify_generation_credential_details(
        credential=credential,
        provider_document=provider_document,
    )

    assert result.valid is False
    assert result.failure_reason == "invalid-public-key"


def test_boolean_verification_wrapper_is_preserved() -> None:
    credential, provider_document = create_test_credential_and_document()

    assert verify_generation_credential(
        credential=credential,
        provider_document=provider_document,
    )
