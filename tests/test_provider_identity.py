import sys
from pathlib import Path

IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.crypto.provider_keys import (  # noqa: E402
    decode_public_key,
    generate_provider_key_pair,
)
from app.services.provider_identity_service import (  # noqa: E402
    create_provider_identity_document,
)


def test_create_provider_identity_document() -> None:
    _, public_key = generate_provider_key_pair()

    document = create_provider_identity_document(
        provider_id="gap-demo-provider",
        provider_name="GAP Demo Provider",
        key_id="key-2026-01",
        public_key=public_key,
    )

    assert document.provider_id == "gap-demo-provider"
    assert document.provider_name == "GAP Demo Provider"
    assert len(document.keys) == 1
    assert document.keys[0].key_id == "key-2026-01"
    assert document.keys[0].algorithm == "Ed25519"
    assert document.keys[0].status == "active"


def test_public_key_can_be_decoded() -> None:
    _, public_key = generate_provider_key_pair()

    document = create_provider_identity_document(
        provider_id="gap-demo-provider",
        provider_name="GAP Demo Provider",
        key_id="key-2026-01",
        public_key=public_key,
    )

    decoded_key = decode_public_key(
        document.keys[0].public_key,
    )

    assert decoded_key is not None
