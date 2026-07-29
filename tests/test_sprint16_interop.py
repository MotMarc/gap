import base64
import binascii
import json
import struct
import zipfile
import zlib
from datetime import datetime, timezone
from io import BytesIO

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from app.crypto.provider_keys import encode_public_key
from app.main import app
from gap_sdk import (
    GapPackage,
    GapProvider,
    GapServiceClient,
    GapVerifier,
    GenerationRequest,
    HttpGenerationProviderAdapter,
    PNG_BINDING,
    RAW_BINDING,
    VerificationLevel,
    calculate_png_binding_digest,
    embed_credential_in_png,
    extract_credential_from_png,
    negotiate,
    remove_gap_png_metadata,
)
from gap_sdk.conformance import ConformanceCase, create_report, verify_report
from gap_sdk.errors import CompatibilityError, MediaBindingError, PackageError
from gap_sdk.models import ProviderIdentity
from gap_sdk.onboarding import prepare_onboarding_package, validate_onboarding_package


def _chunk(kind, data):
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    )


def _png():
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + _chunk(b"tEXt", b"ordinary\x00metadata")
        + _chunk(b"IDAT", zlib.compress(b"\x00\x01\x02\x03\xff"))
        + _chunk(b"IEND", b"")
    )


@pytest.fixture
def provider(tmp_path):
    private = Ed25519PrivateKey.generate()
    identity = ProviderIdentity(
        provider_id="sprint16-test-provider",
        provider_name="Sprint 16 TEST ONLY",
        active_key_id="test-key",
        keys=[
            {
                "key_id": "test-key",
                "public_key": encode_public_key(private.public_key()),
                "status": "active",
                "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            }
        ],
    )

    class Signer:
        key_id = "test-key"
        public_key_base64 = encode_public_key(private.public_key())

        def sign(self, payload):
            return private.sign(payload)

    return GapProvider(identity, Signer())


def _credential(provider, png=None, profile=RAW_BINDING):
    artifact = png or b"artifact"
    digest_source = (
        remove_gap_png_metadata(artifact) if profile == PNG_BINDING else artifact
    )
    return provider.issue_credential(
        digest_source,
        {"model": "test", "media_type": "image/png"},
        binding_profile=profile,
    )


def test_service_discovery_and_negotiation():
    client = TestClient(app)
    response = client.get("/.well-known/gap.json")
    assert response.status_code == 200
    document = response.json()
    assert document["discovery_is_trust_root"] is False
    assert document["application_version"] == "0.16.0"
    assert (
        negotiate(document, binding_profile=PNG_BINDING).binding_profile == PNG_BINDING
    )
    with pytest.raises(CompatibilityError):
        negotiate(document, binding_profile="gap-jpeg-embedded-v1")


def test_client_typed_discovery():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json=TestClient(app).get("/.well-known/gap.json").json()
        )
    )
    capabilities = GapServiceClient("https://gap.test", transport=transport).discover()
    assert capabilities.application_version == "0.16.0"


def test_png_embed_extract_and_normalized_digest(provider):
    original = _png()
    credential = _credential(provider, original, PNG_BINDING)
    embedded = embed_credential_in_png(original, credential)
    assert embedded != original
    assert remove_gap_png_metadata(embedded) == original
    assert calculate_png_binding_digest(embedded) == calculate_png_binding_digest(
        original
    )
    assert extract_credential_from_png(embedded) == credential
    assert (
        GapVerifier(trust_material=None)
        .verify(embedded, credential, level=VerificationLevel.CRYPTOGRAPHIC)
        .artifact_integrity_valid
    )


def test_png_tampering_crc_duplicate_truncation_and_profile_confusion(provider):
    original = _png()
    credential = _credential(provider, original, PNG_BINDING)
    embedded = embed_credential_in_png(original, credential)
    with pytest.raises(MediaBindingError):
        embed_credential_in_png(embedded, credential)
    gap_chunk = embedded[embedded.index(b"gaPc") - 4 : -12]
    duplicate = embedded[:-12] + gap_chunk + embedded[-12:]
    with pytest.raises(MediaBindingError, match="duplicate"):
        extract_credential_from_png(duplicate)
    corrupt = bytearray(embedded)
    corrupt[-1] ^= 1
    with pytest.raises(MediaBindingError, match="CRC"):
        extract_credential_from_png(bytes(corrupt))
    with pytest.raises(MediaBindingError):
        extract_credential_from_png(embedded[:-1])
    raw = _credential(provider, original, RAW_BINDING)
    with pytest.raises(MediaBindingError, match="not signed for PNG"):
        embed_credential_in_png(original, raw)


def test_historical_raw_and_unknown_profile(provider):
    credential = _credential(provider)
    payload = credential.model_dump(mode="json")
    payload["payload"]["artifacts"][0].pop("binding_profile")
    historical = type(credential).model_validate(payload)
    assert (
        GapVerifier()
        .verify(b"artifact", historical, level=VerificationLevel.CRYPTOGRAPHIC)
        .artifact_integrity_valid
    )
    payload["payload"]["artifacts"][0]["binding_profile"] = "gap-unknown-v1"
    with pytest.raises(Exception, match="Unsupported signed binding"):
        GapVerifier().verify(b"artifact", payload)


def test_package_determinism_integrity_extract_and_no_overwrite(provider, tmp_path):
    credential = _credential(provider)
    fixed = datetime(2026, 1, 1, tzinfo=timezone.utc)
    one = GapPackage.create(b"artifact", credential, created_at=fixed)
    two = GapPackage.create(b"artifact", credential, created_at=fixed)
    assert one == two
    assert GapPackage.verify_integrity(one)
    destination = tmp_path / "out"
    assert GapPackage.extract(one, destination)
    with pytest.raises(PackageError, match="overwrite"):
        GapPackage.extract(one, destination)


def test_package_member_tamper_and_traversal_rejected(provider):
    raw = GapPackage.create(b"artifact", _credential(provider))
    source = zipfile.ZipFile(BytesIO(raw))
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for item in source.infolist():
            value = source.read(item)
            archive.writestr(
                item, value + b"x" if item.filename.startswith("artifact/") else value
            )
    with pytest.raises(PackageError, match="integrity"):
        GapPackage.verify_integrity(output.getvalue())
    traversal = BytesIO()
    with zipfile.ZipFile(traversal, "w") as archive:
        archive.writestr("../escape", b"x")
    with pytest.raises(PackageError, match="unsafe"):
        GapPackage.open(traversal.getvalue())


def test_http_generation_adapter_capabilities_request_id_and_redaction():
    png = _png()

    def handler(request):
        if request.url.path.endswith("generation-provider.json"):
            return httpx.Response(
                200,
                json={
                    "provider_name": "External TEST",
                    "media_types": ["image/png"],
                    "maximum_prompt_length": 100,
                    "maximum_response_bytes": 10000,
                    "deterministic": True,
                },
            )
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "artifact_base64": base64.b64encode(png).decode(),
                "media_type": "image/png",
                "filename": "generated.png",
                "model_id": "pilot-v1",
                "request_id": body["request_id"],
            },
        )

    adapter = HttpGenerationProviderAdapter(
        "http://127.0.0.1",
        transport=httpx.MockTransport(handler),
        authorization="secret",
    )
    result = adapter.generate(
        GenerationRequest(prompt="hello", request_id="request-16")
    )
    assert result.artifact == png and result.request_id == "request-16"
    assert "secret" not in repr(adapter)


def test_onboarding_and_conformance_integrity(provider):
    onboarding = prepare_onboarding_package(provider.identity, _credential(provider))
    validate_onboarding_package(onboarding)
    onboarding["application"]["contains_private_key"] = True
    with pytest.raises(PackageError):
        validate_onboarding_package(onboarding)
    report = create_report(
        "provider",
        [
            ConformanceCase(case_id="optional", required=False, status="skipped"),
            ConformanceCase(case_id="required", status="passed"),
        ],
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert report.passed and verify_report(report)
    tampered = report.model_copy(update={"passed": False})
    assert not verify_report(tampered)
    failed = create_report(
        "provider",
        [ConformanceCase(case_id="required", status="skipped")],
    )
    assert not failed.passed
