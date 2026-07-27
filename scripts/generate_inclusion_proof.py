import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "implementation"))

from app.core.repositories import transparency_log_repository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a transparency inclusion proof."
    )
    parser.add_argument("--entry-id", required=True)
    parser.add_argument("--tree-size", type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        print(f"Refusing to overwrite {args.output.name}.", file=sys.stderr)
        return 1
    try:
        entry = transparency_log_repository.get(args.entry_id)
        proof = transparency_log_repository.inclusion_proof(
            args.entry_id, args.tree_size
        )
        head = next(
            item
            for item in transparency_log_repository.list_tree_heads()
            if item.payload.tree_size == proof.tree_size
        )
    except (LookupError, ValueError, StopIteration) as error:
        print(f"Proof generation failed: {error}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "entry": entry.model_dump(mode="json"),
                "tree_head": head.model_dump(mode="json"),
                "proof": proof.model_dump(mode="json"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"entry_id={entry.entry_id} tree_size={proof.tree_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
