import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "implementation"))

from app.core.repositories import checkpoint_gossip_repository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a public GAP gossip package.")
    parser.add_argument("destination", type=Path)
    parser.add_argument("--gossip-id")
    parser.add_argument(
        "--export-id",
        help="Assign a new package envelope ID without changing signed evidence.",
    )
    args = parser.parse_args()
    packages = checkpoint_gossip_repository.list_all()
    package = (
        checkpoint_gossip_repository.get(args.gossip_id)
        if args.gossip_id
        else packages[-1]
        if packages
        else None
    )
    if package is None:
        print("No gossip package is available.", file=sys.stderr)
        return 1
    if args.export_id:
        package = package.model_copy(update={"gossip_id": args.export_id})
    if args.destination.exists():
        print("Refusing to overwrite an existing file.", file=sys.stderr)
        return 1
    args.destination.write_text(
        package.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    print(f"Exported gossip package {package.gossip_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
