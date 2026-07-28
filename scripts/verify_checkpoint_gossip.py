import argparse
import sys
from pathlib import Path

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "implementation"))

from app.core.transparency_log_config import TRUSTED_TRANSPARENCY_LOGS  # noqa: E402
from app.core.transparency_witness_config import (  # noqa: E402
    transparency_witness_repository,
)
from app.schemas.checkpoint_gossip import CheckpointGossipPackage  # noqa: E402
from app.services.checkpoint_gossip_repository import (  # noqa: E402
    MAXIMUM_GOSSIP_FILE_SIZE,
)
from app.services.checkpoint_gossip_service import (  # noqa: E402
    verify_checkpoint_gossip_package,
)
from app.services.witness_quorum_service import (  # noqa: E402
    WitnessQuorumPolicy,
)


def load_package(path: Path) -> CheckpointGossipPackage:
    if path.stat().st_size > MAXIMUM_GOSSIP_FILE_SIZE:
        raise ValueError("gossip-package-too-large")
    return CheckpointGossipPackage.model_validate_json(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a GAP gossip package.")
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    try:
        package = load_package(args.package)
        result = verify_checkpoint_gossip_package(
            package,
            TRUSTED_TRANSPARENCY_LOGS,
            transparency_witness_repository,
            WitnessQuorumPolicy(),
        )
    except (OSError, ValueError, ValidationError) as error:
        print(f"Gossip verification failed: {error}", file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    return 0 if result.checkpoint_gossip_consistent else 1


if __name__ == "__main__":
    raise SystemExit(main())
