from __future__ import annotations

import binascii
import hashlib
import json
import struct
from dataclasses import dataclass

from .errors import MediaBindingError
from .interop import MAX_EMBEDDED_METADATA_SIZE, PNG_BINDING, signed_binding_profile
from .models import GapCredential
from .serialization import canonical_json

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
GAP_CHUNK_TYPE = b"gaPc"
MAX_CHUNK_SIZE = 64 * 1024 * 1024


@dataclass(frozen=True)
class _Chunk:
    kind: bytes
    data: bytes
    encoded: bytes


def _parse(png: bytes) -> list[_Chunk]:
    if not isinstance(png, bytes) or not png.startswith(PNG_SIGNATURE):
        raise MediaBindingError("Artifact is not a PNG.")
    chunks: list[_Chunk] = []
    offset = len(PNG_SIGNATURE)
    seen_iend = False
    while offset < len(png):
        if len(png) - offset < 12:
            raise MediaBindingError("PNG contains a truncated chunk.")
        length = struct.unpack(">I", png[offset : offset + 4])[0]
        if length > MAX_CHUNK_SIZE or offset + 12 + length > len(png):
            raise MediaBindingError("PNG chunk length is invalid.")
        kind = png[offset + 4 : offset + 8]
        if not all(65 <= byte <= 90 or 97 <= byte <= 122 for byte in kind):
            raise MediaBindingError("PNG chunk type is invalid.")
        end = offset + 12 + length
        data = png[offset + 8 : offset + 8 + length]
        expected = struct.unpack(">I", png[offset + 8 + length : end])[0]
        actual = binascii.crc32(kind + data) & 0xFFFFFFFF
        if expected != actual:
            raise MediaBindingError("PNG chunk CRC is invalid.")
        if seen_iend:
            raise MediaBindingError("PNG has trailing bytes after IEND.")
        chunks.append(_Chunk(kind, data, png[offset:end]))
        seen_iend = kind == b"IEND"
        offset = end
    if not chunks or chunks[0].kind != b"IHDR" or not seen_iend:
        raise MediaBindingError("PNG chunk ordering is invalid.")
    if sum(chunk.kind == GAP_CHUNK_TYPE for chunk in chunks) > 1:
        raise MediaBindingError("PNG contains duplicate GAP credentials.")
    gap = next((chunk for chunk in chunks if chunk.kind == GAP_CHUNK_TYPE), None)
    if gap and len(gap.data) > MAX_EMBEDDED_METADATA_SIZE:
        raise MediaBindingError("Embedded GAP credential exceeds the size limit.")
    return chunks


def remove_gap_png_metadata(png: bytes) -> bytes:
    return PNG_SIGNATURE + b"".join(
        chunk.encoded for chunk in _parse(png) if chunk.kind != GAP_CHUNK_TYPE
    )


def calculate_png_binding_digest(png: bytes) -> str:
    return hashlib.sha256(remove_gap_png_metadata(png)).hexdigest()


def extract_credential_from_png(png: bytes) -> GapCredential:
    chunk = next((item for item in _parse(png) if item.kind == GAP_CHUNK_TYPE), None)
    if chunk is None:
        raise MediaBindingError("PNG does not contain a GAP credential.")
    try:
        credential = GapCredential.model_validate(
            json.loads(chunk.data.decode("utf-8"))
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise MediaBindingError("Embedded GAP credential is malformed.") from exc
    if signed_binding_profile(credential) != PNG_BINDING:
        raise MediaBindingError("Embedded credential has the wrong binding profile.")
    return credential


def embed_credential_in_png(
    png: bytes, credential: GapCredential | dict, *, replace: bool = False
) -> bytes:
    parsed = _parse(png)
    existing = any(chunk.kind == GAP_CHUNK_TYPE for chunk in parsed)
    if existing and not replace:
        raise MediaBindingError("PNG already contains a GAP credential.")
    credential = GapCredential.model_validate(credential)
    if signed_binding_profile(credential) != PNG_BINDING:
        raise MediaBindingError("Credential is not signed for PNG embedding.")
    if credential.payload.artifacts[0].digest.value != calculate_png_binding_digest(
        png
    ):
        raise MediaBindingError("Credential does not bind this normalized PNG.")
    payload = canonical_json(credential.model_dump(mode="json", exclude_none=True))
    if len(payload) > MAX_EMBEDDED_METADATA_SIZE:
        raise MediaBindingError("Embedded GAP credential exceeds the size limit.")
    crc = binascii.crc32(GAP_CHUNK_TYPE + payload) & 0xFFFFFFFF
    encoded = (
        struct.pack(">I", len(payload))
        + GAP_CHUNK_TYPE
        + payload
        + struct.pack(">I", crc)
    )
    output = bytearray(PNG_SIGNATURE)
    for chunk in parsed:
        if chunk.kind == GAP_CHUNK_TYPE:
            continue
        if chunk.kind == b"IEND":
            output.extend(encoded)
        output.extend(chunk.encoded)
    return bytes(output)


def verify_embedded_png(png: bytes, verifier, *, level="full"):
    credential = extract_credential_from_png(png)
    return verifier.verify(png, credential, level=level)
