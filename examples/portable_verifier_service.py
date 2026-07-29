"""Stateless portable verifier used for isolated cross-installation validation."""

from __future__ import annotations

import base64
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from gap_sdk import GapVerifier, VerificationLevel
from gap_sdk.errors import GapError

MAX_ARTIFACT_BYTES = 20 * 1024 * 1024
DATABASE_PATH = Path(os.environ["GAP_VERIFIER_DATABASE"]).resolve()
RUNTIME_DIRECTORY = Path(os.environ["GAP_VERIFIER_RUNTIME"]).resolve()
RUNTIME_DIRECTORY.mkdir(parents=True, exist_ok=True)
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(DATABASE_PATH) as connection:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS installation_meta "
        "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT OR REPLACE INTO installation_meta(key,value) VALUES (?,?)",
        ("role", "portable-verifier"),
    )

app = FastAPI(title="GAP Portable Verifier", version="1.0.0")


class PortableVerificationRequest(BaseModel):
    artifact_base64: str = Field(max_length=(MAX_ARTIFACT_BYTES * 4 // 3) + 8)
    credential: dict
    trust_material: dict
    level: VerificationLevel = VerificationLevel.FULL


@app.get("/health/ready")
def readiness():
    return {
        "status": "ready",
        "version": "1.0.0",
        "role": "portable-verifier",
        "persistence": "isolated-sqlite",
    }


@app.post("/portable/verify")
def verify_portable(request: PortableVerificationRequest):
    try:
        artifact = base64.b64decode(request.artifact_base64, validate=True)
        if len(artifact) > MAX_ARTIFACT_BYTES:
            raise ValueError
        verifier = GapVerifier.from_trust_material(request.trust_material)
        result = verifier.verify(artifact, request.credential, level=request.level)
        return result.model_dump(mode="json", exclude_none=True)
    except (GapError, ValueError) as exc:
        raise HTTPException(
            status_code=422, detail="Portable verification input was rejected."
        ) from exc
