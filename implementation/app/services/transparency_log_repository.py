import os
import re
import tempfile
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.crypto.canonical_json import canonicalise_model
from app.crypto.merkle import (
    calculate_merkle_root,
    generate_consistency_proof,
    generate_inclusion_proof,
    hash_leaf,
)
from app.schemas.signed_tree_head import SignedTreeHead
from app.schemas.transparency_proof import ConsistencyProof, InclusionProof
from app.services.transparency_entry_service import validate_entry_digest
from app.services.transparency_log_service import create_signed_tree_head
from app.services.transparency_log_service import verify_signed_tree_head
from app.schemas.transparency_entry import TransparencyLogEntry
from app.core.transparency_log_config import TRUSTED_TRANSPARENCY_LOGS


class TransparencyLogRepositoryError(ValueError):
    pass


class TransparencyEntryNotFoundError(LookupError):
    pass


class TransparencyTreeHeadNotFoundError(LookupError):
    pass


class TransparencyLogRepository:
    def __init__(self, operator, runtime_directory: Path | None = None) -> None:
        self.operator = operator
        self._entries = []
        self._tree_heads: dict[str, SignedTreeHead] = {}
        self.runtime_directory = runtime_directory
        self.invalid_runtime_object_count = 0
        if runtime_directory is not None:
            self._load_runtime()

    @staticmethod
    def _write_atomic(model, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(model.model_dump_json(indent=2) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        except Exception:
            Path(temporary).unlink(missing_ok=True)
            raise

    def _load_runtime(self) -> None:
        entry_adapter = TypeAdapter(TransparencyLogEntry)
        entries_directory = self.runtime_directory / "entries"
        for path in sorted(entries_directory.glob("*.json")):
            try:
                entry = entry_adapter.validate_json(path.read_text(encoding="utf-8"))
                self.append(entry, persist=False)
            except (OSError, ValueError, ValidationError):
                self.invalid_runtime_object_count += 1
                break
        heads_directory = self.runtime_directory / "tree-heads"
        for path in sorted(heads_directory.glob("*.json")):
            try:
                tree_head = SignedTreeHead.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
                if not verify_signed_tree_head(tree_head, TRUSTED_TRANSPARENCY_LOGS):
                    raise ValueError("invalid-tree-head")
                self.store_tree_head(tree_head, persist=False)
            except (OSError, ValueError, ValidationError):
                self.invalid_runtime_object_count += 1

    def append(self, entry, persist: bool = True) -> int:
        if not validate_entry_digest(entry):
            raise TransparencyLogRepositoryError("invalid-object-digest")
        if any(item.entry_id == entry.entry_id for item in self._entries):
            raise TransparencyLogRepositoryError("duplicate-entry-id")
        if any(
            item.entry_type == entry.entry_type and item.object_id == entry.object_id
            for item in self._entries
        ):
            raise TransparencyLogRepositoryError("duplicate-object-binding")
        self._entries.append(entry.model_copy(deep=True))
        index = len(self._entries) - 1
        if persist and self.runtime_directory is not None:
            destination = (
                self.runtime_directory / "entries" / f"{index:012d}-entry.json"
            )
            if destination.exists():
                self._entries.pop()
                raise TransparencyLogRepositoryError("entry-file-already-exists")
            self._write_atomic(entry, destination)
        return index

    def get(self, entry_id: str):
        for entry in self._entries:
            if entry.entry_id == entry_id:
                return entry.model_copy(deep=True)
        raise TransparencyEntryNotFoundError(f"Unknown transparency entry: {entry_id}")

    def get_by_index(self, index: int):
        if index < 0 or index >= len(self._entries):
            raise TransparencyEntryNotFoundError("Unknown transparency leaf index.")
        return self._entries[index].model_copy(deep=True)

    def find_object(self, entry_type: str, object_id: str):
        for index, entry in enumerate(self._entries):
            if entry.entry_type == entry_type and entry.object_id == object_id:
                return index, entry.model_copy(deep=True)
        return None

    def list_entries(self):
        return [item.model_copy(deep=True) for item in self._entries]

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def _leaf_hashes(self, tree_size: int | None = None) -> list[bytes]:
        size = len(self._entries) if tree_size is None else tree_size
        if size < 0 or size > len(self._entries):
            raise TransparencyLogRepositoryError("invalid-tree-size")
        return [hash_leaf(canonicalise_model(item)) for item in self._entries[:size]]

    def current_root(self) -> str:
        return calculate_merkle_root(self._leaf_hashes()).hex()

    def create_current_tree_head(self, timestamp=None, tree_head_id=None):
        tree_head = create_signed_tree_head(
            self.operator,
            self.entry_count,
            self.current_root(),
            timestamp,
            tree_head_id,
        )
        self.store_tree_head(tree_head)
        return tree_head.model_copy(deep=True)

    def store_tree_head(self, tree_head: SignedTreeHead, persist: bool = True) -> None:
        if tree_head.payload.tree_size > self.entry_count:
            raise TransparencyLogRepositoryError("tree-size-exceeds-entry-count")
        if tree_head.payload.tree_head_id in self._tree_heads:
            raise TransparencyLogRepositoryError("duplicate-tree-head-id")
        for existing in self._tree_heads.values():
            if (
                existing.payload.tree_size == tree_head.payload.tree_size
                and existing.payload.root_hash != tree_head.payload.root_hash
            ):
                raise TransparencyLogRepositoryError("split-view-detected")
        expected = calculate_merkle_root(
            self._leaf_hashes(tree_head.payload.tree_size)
        ).hex()
        if tree_head.payload.root_hash != expected:
            raise TransparencyLogRepositoryError("tree-head-root-mismatch")
        self._tree_heads[tree_head.payload.tree_head_id] = tree_head.model_copy(
            deep=True
        )
        if persist and self.runtime_directory is not None:
            safe_id = re.sub(r"[^A-Za-z0-9._-]", "_", tree_head.payload.tree_head_id)
            destination = self.runtime_directory / "tree-heads" / f"{safe_id}.json"
            if destination.exists():
                del self._tree_heads[tree_head.payload.tree_head_id]
                raise TransparencyLogRepositoryError("tree-head-file-already-exists")
            self._write_atomic(tree_head, destination)

    def list_tree_heads(self):
        return [
            item.model_copy(deep=True)
            for item in sorted(
                self._tree_heads.values(),
                key=lambda value: (
                    value.payload.tree_size,
                    value.payload.timestamp,
                ),
            )
        ]

    def get_tree_head(self, tree_head_id: str):
        try:
            return self._tree_heads[tree_head_id].model_copy(deep=True)
        except KeyError as error:
            raise TransparencyTreeHeadNotFoundError(
                f"Unknown tree head: {tree_head_id}"
            ) from error

    def latest_tree_head(self):
        values = self.list_tree_heads()
        return values[-1] if values else None

    def inclusion_proof(self, entry_id: str, tree_size: int | None = None):
        self.get(entry_id)
        index = next(
            index
            for index, item in enumerate(self._entries)
            if item.entry_id == entry_id
        )
        size = self.entry_count if tree_size is None else tree_size
        if index >= size or size <= 0 or size > self.entry_count:
            raise TransparencyLogRepositoryError("invalid-tree-size")
        leaves = self._leaf_hashes(size)
        root = calculate_merkle_root(leaves)
        return InclusionProof(
            log_id=self.operator.log_id,
            tree_size=size,
            leaf_index=index,
            entry_id=entry_id,
            leaf_hash=leaves[index].hex(),
            root_hash=root.hex(),
            audit_path=tuple(
                item.hex() for item in generate_inclusion_proof(leaves, index)
            ),
        )

    def consistency_proof(self, old_size: int, new_size: int):
        if old_size < 0 or old_size > new_size or new_size > self.entry_count:
            raise TransparencyLogRepositoryError("invalid-tree-size")
        leaves = self._leaf_hashes(new_size)
        old_root = calculate_merkle_root(leaves[:old_size])
        new_root = calculate_merkle_root(leaves)
        return ConsistencyProof(
            log_id=self.operator.log_id,
            old_tree_size=old_size,
            new_tree_size=new_size,
            old_root_hash=old_root.hex(),
            new_root_hash=new_root.hex(),
            consistency_path=tuple(
                item.hex() for item in generate_consistency_proof(leaves, old_size)
            ),
        )
