import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "implementation"))

from app.core.repositories import transparency_log_repository  # noqa: E402
from app.services.transparency_log_repository import TransparencyLogRepository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the current signed tree head.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    tree_head = transparency_log_repository.latest_tree_head()
    if tree_head is None:
        print("No signed tree head is available.", file=sys.stderr)
        return 1
    if args.output.exists() and not args.overwrite:
        print(f"Refusing to overwrite {args.output.name}.", file=sys.stderr)
        return 1
    TransparencyLogRepository._write_atomic(tree_head, args.output.resolve())
    payload = tree_head.payload
    print(
        f"tree_head_id={payload.tree_head_id} tree_size={payload.tree_size} "
        f"root_hash={payload.root_hash} timestamp={payload.timestamp.isoformat()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
