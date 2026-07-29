from __future__ import annotations

import hashlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from .errors import CredentialError
from .models import GapCredential
from .serialization import pretty_json


def resolve_local_file(path: str | Path) -> Path:
    """Resolve a file path selected by the local SDK caller.

    This is intentionally not a sandbox: SDK callers may select files outside the
    current directory. Protocol data must never be passed to this function.
    """
    value = str(path)
    if not value or "\x00" in value:
        raise CredentialError("Artifact path is invalid.")
    try:
        resolved = Path(path).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise CredentialError("Artifact file could not be opened.") from exc
    if not resolved.is_file():
        raise CredentialError("Artifact path must identify a file.")
    return resolved


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with resolve_local_file(path).open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def credential_path_for_artifact(path: str | Path) -> Path:
    artifact = Path(path)
    return artifact.with_name(artifact.name + ".gap.json")


def write_sidecar(
    artifact_path: str | Path,
    credential: GapCredential,
    *,
    overwrite: bool = False,
) -> Path:
    destination = credential_path_for_artifact(artifact_path)
    if destination.exists() and not overwrite:
        raise CredentialError("Credential sidecar already exists.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=destination.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        stream.write(
            pretty_json(
                {
                    "sidecar_version": "gap-sidecar-v1",
                    "credential": credential.model_dump(mode="json", exclude_none=True),
                }
            )
        )
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def read_sidecar(artifact_path: str | Path) -> GapCredential:
    import json

    try:
        data = json.loads(
            credential_path_for_artifact(artifact_path).read_text("utf-8")
        )
        return GapCredential.model_validate(data["credential"])
    except (OSError, ValueError, KeyError) as exc:
        raise CredentialError("Credential sidecar is missing or malformed.") from exc
