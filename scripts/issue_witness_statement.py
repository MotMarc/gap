import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "implementation"))

from app.core.repositories import transparency_log_repository  # noqa: E402
from app.core.transparency_log_config import REFERENCE_TRANSPARENCY_LOG  # noqa: E402
from app.core.transparency_witness_config import (  # noqa: E402
    REFERENCE_TRANSPARENCY_WITNESS,
)
from app.services.transparency_log_identity_service import (  # noqa: E402
    create_transparency_log_identity_document,
)
from app.services.transparency_witness_service import issue_witness_statement  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue a local witness statement.")
    parser.add_argument("destination", type=Path)
    parser.add_argument("--tree-head-id")
    args = parser.parse_args()
    if args.destination.exists():
        print("Refusing to overwrite an existing file.", file=sys.stderr)
        return 1
    tree_head = (
        transparency_log_repository.get_tree_head(args.tree_head_id)
        if args.tree_head_id
        else transparency_log_repository.latest_tree_head()
    )
    if tree_head is None:
        print("No signed tree head is available.", file=sys.stderr)
        return 1
    try:
        statement = issue_witness_statement(
            REFERENCE_TRANSPARENCY_WITNESS,
            tree_head,
            create_transparency_log_identity_document(REFERENCE_TRANSPARENCY_LOG),
        )
        args.destination.write_text(
            statement.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError) as error:
        print(f"Witness statement issuance failed: {error}", file=sys.stderr)
        return 1
    print(f"Issued witness statement {statement.payload.statement_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
