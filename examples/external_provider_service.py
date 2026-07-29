"""Independent deterministic pilot provider. It is not a commercial AI vendor."""

import base64
import binascii
import hashlib
import struct

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="GAP sample external provider", version="1.0.0")


class Request(BaseModel):
    prompt: str
    request_id: str | None = None
    media_type: str = "image/png"


def chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    )


def png_for(prompt: str) -> bytes:
    import zlib

    colour = hashlib.sha256(prompt.encode()).digest()[:3]
    raw = b"\x00" + colour + b"\xff"
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


@app.get("/.well-known/generation-provider.json")
def discover():
    return {
        "provider_name": "GAP Sample External Provider",
        "media_types": ["image/png"],
        "maximum_prompt_length": 4096,
        "maximum_response_bytes": 1048576,
        "deterministic": True,
    }


@app.post("/generate")
def generate(request: Request):
    artifact = png_for(request.prompt)
    return {
        "artifact_base64": base64.b64encode(artifact).decode(),
        "media_type": "image/png",
        "filename": "generated.png",
        "model_id": "sample-deterministic-png-v1",
        "request_id": request.request_id,
    }
