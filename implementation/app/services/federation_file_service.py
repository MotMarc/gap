import json
import os
import tempfile
from pathlib import Path

from app.schemas.federation_bundle import FederationBundle
from app.services.federation_bundle_service import import_federation_bundle


MAX_BUNDLE_FILE_BYTES = 5 * 1024 * 1024
MAX_BUNDLE_ATTESTATIONS = 1000


def read_bundle_file(path: Path) -> FederationBundle:
    if path.stat().st_size > MAX_BUNDLE_FILE_BYTES:
        raise ValueError("Federation bundle exceeds the maximum file size.")
    bundle = FederationBundle.model_validate_json(path.read_text(encoding="utf-8"))
    if len(bundle.payload.attestations) > MAX_BUNDLE_ATTESTATIONS:
        raise ValueError("Federation bundle exceeds the attestation limit.")
    return bundle


def write_bundle_atomically(
    bundle: FederationBundle, destination: Path, overwrite: bool = False
) -> None:
    destination = destination.resolve()
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"Refusing to overwrite existing file: {destination.name}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = (
        json.dumps(
            bundle.model_dump(mode="json", exclude_none=True),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def load_accepted_bundle_directory(
    directory: Path, authority_repository, bundle_repository
) -> tuple[int, int]:
    accepted = invalid = 0
    if not directory.exists():
        return accepted, invalid
    parsed: list[FederationBundle] = []
    for path in directory.glob("*.json"):
        try:
            parsed.append(read_bundle_file(path))
        except (OSError, ValueError):
            invalid += 1
    grouped: dict[str, list[FederationBundle]] = {}
    for bundle in parsed:
        grouped.setdefault(bundle.payload.registry_authority_id, []).append(bundle)
    for bundles in grouped.values():
        for bundle in sorted(bundles, key=lambda item: item.payload.sequence_number):
            result = import_federation_bundle(
                bundle, authority_repository, bundle_repository
            )
            if result.imported:
                accepted += 1
            else:
                invalid += 1
                # Fail closed for the remainder of a broken authority chain.
                break
    return accepted, invalid
