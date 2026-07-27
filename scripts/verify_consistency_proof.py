import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "implementation"))

from app.core.transparency_log_config import TRUSTED_TRANSPARENCY_LOGS  # noqa: E402
from app.schemas.signed_tree_head import SignedTreeHead  # noqa: E402
from app.schemas.transparency_proof import ConsistencyProof  # noqa: E402
from app.services.transparency_verification_service import verify_consistency  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a Merkle consistency proof.")
    parser.add_argument("--old-tree-head", required=True, type=Path)
    parser.add_argument("--new-tree-head", required=True, type=Path)
    parser.add_argument("--proof", required=True, type=Path)
    args = parser.parse_args()
    try:
        old = SignedTreeHead.model_validate_json(
            args.old_tree_head.read_text(encoding="utf-8-sig")
        )
        new = SignedTreeHead.model_validate_json(
            args.new_tree_head.read_text(encoding="utf-8-sig")
        )
        proof = ConsistencyProof.model_validate_json(
            args.proof.read_text(encoding="utf-8-sig")
        )
        result = verify_consistency(old, new, proof, TRUSTED_TRANSPARENCY_LOGS)
    except (OSError, ValueError) as error:
        print(json.dumps({"valid": False, "failure_reason": str(error)}))
        return 1
    print(result.model_dump_json(indent=2))
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
