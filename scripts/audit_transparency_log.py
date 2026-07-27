import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "implementation"))

from app.core.repositories import transparency_log_repository  # noqa: E402
from app.core.transparency_log_config import TRUSTED_TRANSPARENCY_LOGS  # noqa: E402
from app.services.transparency_entry_service import validate_entry_digest  # noqa: E402
from app.services.transparency_log_service import verify_signed_tree_head  # noqa: E402


def main() -> int:
    repository = transparency_log_repository
    errors = repository.invalid_runtime_object_count
    bindings = set()
    for entry in repository.list_entries():
        binding = (entry.entry_type, entry.object_id)
        if binding in bindings or not validate_entry_digest(entry):
            errors += 1
        bindings.add(binding)
    for head in repository.list_tree_heads():
        if not verify_signed_tree_head(head, TRUSTED_TRANSPARENCY_LOGS):
            errors += 1
    print(
        f"entries={repository.entry_count} tree_heads="
        f"{len(repository.list_tree_heads())} current_root={repository.current_root()} "
        f"errors={errors}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
