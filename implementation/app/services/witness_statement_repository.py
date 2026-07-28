import os
import re
import tempfile
from pathlib import Path

from pydantic import ValidationError

from app.schemas.witness_statement import WitnessStatement


class WitnessStatementRepository:
    def __init__(self, runtime_directory: Path | None = None) -> None:
        self._statements: dict[str, WitnessStatement] = {}
        self.runtime_directory = runtime_directory
        self.invalid_runtime_object_count = 0
        if runtime_directory is not None:
            for path in sorted(runtime_directory.glob("*.json")):
                try:
                    self.add(
                        WitnessStatement.model_validate_json(
                            path.read_text(encoding="utf-8")
                        ),
                        persist=False,
                    )
                except (OSError, ValueError, ValidationError):
                    self.invalid_runtime_object_count += 1

    def add(self, statement: WitnessStatement, persist: bool = True) -> None:
        payload = statement.payload
        if payload.statement_id in self._statements:
            raise ValueError("duplicate-witness-statement-id")
        if any(
            item.payload.witness_id == payload.witness_id
            and item.payload.tree_head_id == payload.tree_head_id
            for item in self._statements.values()
        ):
            raise ValueError("duplicate-witness-tree-head-statement")
        self._statements[payload.statement_id] = statement.model_copy(deep=True)
        if persist and self.runtime_directory is not None:
            self.runtime_directory.mkdir(parents=True, exist_ok=True)
            safe = re.sub(r"[^A-Za-z0-9._-]", "_", payload.statement_id)
            destination = self.runtime_directory / f"{safe}.json"
            if destination.exists():
                del self._statements[payload.statement_id]
                raise ValueError("witness-statement-file-already-exists")
            descriptor, temporary = tempfile.mkstemp(
                prefix=f".{safe}.", suffix=".tmp", dir=self.runtime_directory
            )
            try:
                with os.fdopen(
                    descriptor, "w", encoding="utf-8", newline="\n"
                ) as handle:
                    handle.write(statement.model_dump_json(indent=2) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, destination)
            except Exception:
                Path(temporary).unlink(missing_ok=True)
                del self._statements[payload.statement_id]
                raise

    def get(self, statement_id: str) -> WitnessStatement:
        try:
            return self._statements[statement_id].model_copy(deep=True)
        except KeyError as error:
            raise LookupError(f"Unknown witness statement: {statement_id}") from error

    def list_all(self) -> list[WitnessStatement]:
        return [item.model_copy(deep=True) for item in self._statements.values()]

    def list_by_witness(self, witness_id: str):
        return [
            item for item in self.list_all() if item.payload.witness_id == witness_id
        ]

    def list_by_log(self, log_id: str):
        return [item for item in self.list_all() if item.payload.log_id == log_id]

    def list_by_tree_head(self, tree_head_id: str):
        return [
            item
            for item in self.list_all()
            if item.payload.tree_head_id == tree_head_id
        ]

    def list_by_log_and_tree_size(self, log_id: str, tree_size: int):
        return [
            item
            for item in self.list_all()
            if item.payload.log_id == log_id and item.payload.tree_size == tree_size
        ]

    def find_by_witness_and_tree_head(self, witness_id: str, tree_head_id: str):
        return next(
            (
                item
                for item in self.list_all()
                if item.payload.witness_id == witness_id
                and item.payload.tree_head_id == tree_head_id
            ),
            None,
        )
