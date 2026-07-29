from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .errors import TrustMaterialError
from .trust import load_trust_material, save_trust_material


class TrustMaterialCache:
    def __init__(
        self,
        directory: str | Path,
        *,
        maximum_bytes: int = 10 * 1024 * 1024,
        maximum_age_seconds: int = 24 * 60 * 60,
    ):
        self.directory = Path(directory)
        self.maximum_bytes = maximum_bytes
        self.maximum_age_seconds = maximum_age_seconds
        self.path = self.directory / "public-trust-material.json"

    def load(self, *, allow_stale: bool = False):
        if self.path.stat().st_size > self.maximum_bytes:
            raise TrustMaterialError("Cached trust material exceeds the size limit.")
        material = load_trust_material(self.path)
        exported_at = material.state.get("exported_at")
        if exported_at:
            timestamp = datetime.fromisoformat(str(exported_at).replace("Z", "+00:00"))
            stale = (
                datetime.now(timezone.utc) - timestamp
            ).total_seconds() > self.maximum_age_seconds
            if stale and not allow_stale:
                raise TrustMaterialError("Cached trust material is stale.")
        return material

    def refresh(self, client):
        state = client.export_trust_material()
        from .serialization import canonical_json

        if len(canonical_json(state)) > self.maximum_bytes:
            raise TrustMaterialError("Trust material exceeds the cache size limit.")
        self.directory.mkdir(parents=True, exist_ok=True)
        save_trust_material(state, self.path, overwrite=True)
        return self.load()
