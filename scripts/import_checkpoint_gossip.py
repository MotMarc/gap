import argparse
import sys
from pathlib import Path

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "implementation"))

from app.core.repositories import checkpoint_gossip_repository  # noqa: E402
from app.core.transparency_log_config import TRUSTED_TRANSPARENCY_LOGS  # noqa: E402
from app.core.transparency_witness_config import (  # noqa: E402
    transparency_witness_repository,
)
from app.services.checkpoint_gossip_service import (  # noqa: E402
    verify_checkpoint_gossip_package,
)
from app.services.witness_quorum_service import WitnessQuorumPolicy  # noqa: E402
from verify_checkpoint_gossip import load_package  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify and atomically import gossip.")
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    try:
        package = load_package(args.package)
        result = verify_checkpoint_gossip_package(
            package,
            TRUSTED_TRANSPARENCY_LOGS,
            transparency_witness_repository,
            WitnessQuorumPolicy(),
            checkpoint_gossip_repository.list_all(),
        )
        if not result.checkpoint_gossip_consistent:
            raise ValueError(result.failure_reason)
        checkpoint_gossip_repository.add(package)
    except (OSError, ValueError, ValidationError) as error:
        print(f"Gossip import rejected: {error}", file=sys.stderr)
        return 1
    print(f"Imported gossip package {package.gossip_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
