from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile

from .errors import PackageError
from .interop import MAX_PACKAGE_SIZE, PACKAGE_FORMAT
from .models import GapCredential
from .serialization import canonical_json
from .version import __version__

MAX_MEMBER_SIZE = 64 * 1024 * 1024
MAX_MEMBERS = 32
MAX_COMPRESSION_RATIO = 200
_FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _safe_member(name: str) -> None:
    path = PurePosixPath(name)
    if (
        not name
        or "\x00" in name
        or "\\" in name
        or path.is_absolute()
        or ".." in path.parts
        or re.match(r"^[A-Za-z]:", name)
    ):
        raise PackageError("Package contains an unsafe member name.")


def _read_archive(source: bytes | str | Path):
    raw = source if isinstance(source, bytes) else Path(source).read_bytes()
    if len(raw) > MAX_PACKAGE_SIZE:
        raise PackageError("Package exceeds the size limit.")
    try:
        archive = zipfile.ZipFile(BytesIO(raw))
        infos = archive.infolist()
    except (OSError, zipfile.BadZipFile) as exc:
        raise PackageError("Package is not a valid ZIP archive.") from exc
    if len(infos) > MAX_MEMBERS:
        raise PackageError("Package contains too many members.")
    names: set[str] = set()
    total = 0
    for info in infos:
        _safe_member(info.filename)
        folded = info.filename.casefold()
        if folded in names:
            raise PackageError("Package contains duplicate member names.")
        names.add(folded)
        if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
            raise PackageError("Package uses unsupported compression.")
        if info.external_attr >> 16 & 0o170000 in {0o120000, 0o060000}:
            raise PackageError("Package links are not allowed.")
        if info.file_size > MAX_MEMBER_SIZE:
            raise PackageError("Package member exceeds the size limit.")
        if (
            info.compress_size
            and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO
        ):
            raise PackageError("Package compression ratio exceeds the limit.")
        total += info.file_size
    if total > MAX_PACKAGE_SIZE:
        raise PackageError("Expanded package exceeds the size limit.")
    return archive, infos


class GapPackage:
    @staticmethod
    def create(
        artifact: bytes | str | Path,
        credential: GapCredential | dict | str | Path,
        output: str | Path | None = None,
        *,
        artifact_name: str | None = None,
        media_type: str | None = None,
        trust_material: bytes | str | Path | dict | None = None,
        overwrite: bool = False,
        created_at: datetime | None = None,
    ) -> bytes | Path:
        artifact_bytes = (
            artifact if isinstance(artifact, bytes) else Path(artifact).read_bytes()
        )
        display_name = artifact_name or (
            Path(artifact).name if not isinstance(artifact, bytes) else "artifact.bin"
        )
        if Path(display_name).name != display_name or "\x00" in display_name:
            raise PackageError("Artifact filename is unsafe.")
        if isinstance(credential, (str, Path)):
            data = json.loads(Path(credential).read_text("utf-8"))
            data = data.get("credential", data)
            credential = GapCredential.model_validate(data)
        else:
            credential = GapCredential.model_validate(credential)
        credential_bytes = canonical_json(credential)
        members = {
            f"artifact/{display_name}": artifact_bytes,
            "credential/credential.gap.json": credential_bytes,
        }
        if trust_material is not None:
            if isinstance(trust_material, dict):
                trust_bytes = canonical_json(trust_material)
            elif isinstance(trust_material, bytes):
                trust_bytes = trust_material
            else:
                trust_bytes = Path(trust_material).read_bytes()
            members["trust/trust-material.json"] = trust_bytes
        manifest = {
            "package_format": PACKAGE_FORMAT,
            "package_version": 1,
            "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
            "artifact_filename": display_name,
            "artifact_media_type": media_type
            or credential.payload.artifacts[0].media_type,
            "artifact_size": len(artifact_bytes),
            "artifact_digest": credential.payload.artifacts[0].digest.model_dump(),
            "binding_profile": credential.payload.artifacts[0].binding_profile,
            "credential_id": credential.payload.credential_id,
            "credential_digest": hashlib.sha256(credential_bytes).hexdigest(),
            "trust_material_present": "trust/trust-material.json" in members,
            "required_verification_level": "full",
            "application_version": __version__,
            "sdk_version": __version__,
            "members": {
                name: {"size": len(value), "sha256": hashlib.sha256(value).hexdigest()}
                for name, value in sorted(members.items())
            },
        }
        members["manifest.json"] = canonical_json(manifest)
        stream = BytesIO()
        with zipfile.ZipFile(
            stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for name, value in sorted(members.items()):
                info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100600 << 16
                archive.writestr(info, value)
        raw = stream.getvalue()
        if len(raw) > MAX_PACKAGE_SIZE:
            raise PackageError("Package exceeds the size limit.")
        if output is None:
            return raw
        destination = Path(output)
        if destination.exists() and not overwrite:
            raise PackageError("Package output already exists.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("wb", dir=destination.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return destination

    @staticmethod
    def open(source: bytes | str | Path) -> dict[str, bytes]:
        archive, infos = _read_archive(source)
        try:
            with archive:
                return {info.filename: archive.read(info) for info in infos}
        except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
            raise PackageError("Package member is corrupt.") from exc

    @classmethod
    def inspect(cls, source: bytes | str | Path) -> dict:
        members = cls.open(source)
        try:
            return json.loads(members["manifest.json"].decode("utf-8"))
        except (KeyError, UnicodeDecodeError, ValueError) as exc:
            raise PackageError("Package manifest is missing or malformed.") from exc

    @classmethod
    def verify_integrity(cls, source: bytes | str | Path) -> bool:
        members = cls.open(source)
        manifest = cls.inspect(source)
        if manifest.get("package_format") != PACKAGE_FORMAT:
            raise PackageError("Unsupported package format.")
        declared = manifest.get("members", {})
        if set(members) != set(declared) | {"manifest.json"}:
            raise PackageError("Package member index does not match.")
        for name, metadata in declared.items():
            value = members[name]
            if len(value) != metadata.get("size") or hashlib.sha256(
                value
            ).hexdigest() != metadata.get("sha256"):
                raise PackageError("Package member integrity check failed.")
        return True

    @classmethod
    def verify(cls, source, verifier, *, level="full"):
        cls.verify_integrity(source)
        members = cls.open(source)
        manifest = cls.inspect(source)
        artifact = members[f"artifact/{manifest['artifact_filename']}"]
        credential = GapCredential.model_validate_json(
            members["credential/credential.gap.json"]
        )
        return verifier.verify(artifact, credential, level=level)

    @classmethod
    def extract(
        cls,
        source: bytes | str | Path,
        destination: str | Path,
        *,
        overwrite: bool = False,
    ) -> list[Path]:
        cls.verify_integrity(source)
        root = Path(destination).resolve()
        root.mkdir(parents=True, exist_ok=True)
        written = []
        for name, value in cls.open(source).items():
            target = (root / PurePosixPath(name)).resolve()
            if root not in target.parents:
                raise PackageError("Package extraction escaped the destination.")
            if target.exists() and not overwrite:
                raise PackageError("Package extraction would overwrite a file.")
            target.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile("wb", dir=target.parent, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(value)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
            written.append(target)
        return written
