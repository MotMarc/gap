import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "implementation"))

from app.core.repositories import transparency_log_repository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a Merkle consistency proof.")
    parser.add_argument("--old-tree-size", required=True, type=int)
    parser.add_argument("--new-tree-size", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        print(f"Refusing to overwrite {args.output.name}.", file=sys.stderr)
        return 1
    try:
        proof = transparency_log_repository.consistency_proof(
            args.old_tree_size, args.new_tree_size
        )
    except ValueError as error:
        print(f"Proof generation failed: {error}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(proof.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"old_tree_size={args.old_tree_size} new_tree_size={args.new_tree_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
