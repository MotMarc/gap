from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from .errors import TrustMaterialError
from .models import TrustMaterialBundle
from .serialization import canonical_json, pretty_json


def load_trust_material(path: str | Path) -> TrustMaterialBundle:
    try:
        bundle = TrustMaterialBundle.model_validate_json(Path(path).read_text("utf-8"))
    except (OSError, ValueError) as exc:
        raise TrustMaterialError("Trust material is missing or malformed.") from exc
    validate_trust_material(bundle)
    return bundle


def validate_trust_material(bundle: TrustMaterialBundle) -> None:
    expected = hashlib.sha256(canonical_json(bundle.state)).hexdigest()
    if bundle.manifest.get("sha256") != expected:
        raise TrustMaterialError("Trust material manifest digest is invalid.")


def save_trust_material(
    state: dict, path: str | Path, *, overwrite: bool = False
) -> Path:
    destination = Path(path)
    if destination.exists() and not overwrite:
        raise TrustMaterialError("Trust material file already exists.")
    bundle = TrustMaterialBundle(
        manifest={
            "format": state.get("bundle_format", "gap-public-state-v2"),
            "sha256": hashlib.sha256(canonical_json(state)).hexdigest(),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "private_data_included": False,
        },
        state=state,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=destination.parent, delete=False
    ) as stream:
        temp = Path(stream.name)
        stream.write(pretty_json(bundle))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, destination)
    return destination
