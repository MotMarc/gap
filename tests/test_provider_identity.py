import sys
from pathlib import Path

IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.crypto.provider_keys import (  # noqa: E402
    decode_public_key,
    encode_public_key,
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

    assert document.gap_version == "0.0.1"
    assert document.provider_id == "gap-demo-provider"
    assert document.provider_name == "GAP Demo Provider"
    assert len(document.keys) == 1

    key = document.keys[0]

    assert key.key_id == "key-2026-01"
    assert key.algorithm == "Ed25519"
    assert key.status == "active"


def test_public_key_encoding_roundtrip() -> None:
    private_key, public_key = generate_provider_key_pair()

    encoded_key = encode_public_key(public_key)
    decoded_key = decode_public_key(encoded_key)

    message = b"GAP public key roundtrip"
    signature = private_key.sign(message)

    decoded_key.verify(signature, message)
