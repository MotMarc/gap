import os
import re
import tempfile
from pathlib import Path

from pydantic import ValidationError

from app.schemas.checkpoint_gossip import CheckpointGossipPackage


MAXIMUM_GOSSIP_FILE_SIZE = 2 * 1024 * 1024


class CheckpointGossipRepository:
    def __init__(self, runtime_directory: Path | None = None) -> None:
        self.runtime_directory = runtime_directory
        self._packages: dict[str, CheckpointGossipPackage] = {}
        self.invalid_runtime_object_count = 0
        if runtime_directory is not None:
            for path in sorted(runtime_directory.glob("*.json")):
                try:
                    if path.stat().st_size > MAXIMUM_GOSSIP_FILE_SIZE:
                        raise ValueError("gossip-package-too-large")
                    self.add(
                        CheckpointGossipPackage.model_validate_json(
                            path.read_text(encoding="utf-8")
                        ),
                        persist=False,
                    )
                except (OSError, ValueError, ValidationError):
                    self.invalid_runtime_object_count += 1

    def add(self, package, persist=True):
        if package.gossip_id in self._packages:
            raise ValueError("duplicate-gossip-id")
        self._packages[package.gossip_id] = package.model_copy(deep=True)
        if persist and self.runtime_directory is not None:
            self.runtime_directory.mkdir(parents=True, exist_ok=True)
            safe = re.sub(r"[^A-Za-z0-9._-]", "_", package.gossip_id)
            destination = self.runtime_directory / f"{safe}.json"
            if destination.exists():
                del self._packages[package.gossip_id]
                raise ValueError("gossip-file-already-exists")
            descriptor, temporary = tempfile.mkstemp(
                prefix=f".{safe}.", suffix=".tmp", dir=self.runtime_directory
            )
            try:
                encoded = package.model_dump_json(indent=2) + "\n"
                if len(encoded.encode("utf-8")) > MAXIMUM_GOSSIP_FILE_SIZE:
                    raise ValueError("gossip-package-too-large")
                with os.fdopen(
                    descriptor, "w", encoding="utf-8", newline="\n"
                ) as handle:
                    handle.write(encoded)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, destination)
            except Exception:
                Path(temporary).unlink(missing_ok=True)
                del self._packages[package.gossip_id]
                raise

    def get(self, gossip_id):
        try:
            return self._packages[gossip_id].model_copy(deep=True)
        except KeyError as error:
            raise LookupError(f"Unknown gossip package: {gossip_id}") from error

    def list_all(self, limit=100):
        if limit < 1 or limit > 500:
            raise ValueError("invalid-gossip-limit")
        return [
            item.model_copy(deep=True)
            for item in sorted(
                self._packages.values(),
                key=lambda package: (
                    package.exported_at,
                    package.gossip_id,
                ),
            )[-limit:]
        ]
