import sys
from pathlib import Path

IMPLEMENTATION_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "implementation"
)

sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.crypto.provider_keys import generate_provider_key_pair
from app.crypto.signatures import (
    sign_payload,
    verify_payload,
)


def test_signature_roundtrip():

    private_key, public_key = generate_provider_key_pair()

    payload = b"Hello GAP"

    signature = sign_payload(
        payload,
        private_key,
    )

    assert verify_payload(
        payload,
        signature,
        public_key,
    )


def test_modified_payload_fails():

    private_key, public_key = generate_provider_key_pair()

    signature = sign_payload(
        b"Hello GAP",
        private_key,
    )

    assert not verify_payload(
        b"Hello Hacked GAP",
        signature,
        public_key,
    )