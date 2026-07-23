import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "implementation"))

from app.core.registry_authority_config import registry_authority_repository  # noqa: E402
from app.services.federation_bundle_service import verify_federation_bundle  # noqa: E402
from app.services.federation_file_service import read_bundle_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a GAP federation bundle.")
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    try:
        result = verify_federation_bundle(
            read_bundle_file(args.bundle), registry_authority_repository
        )
    except (OSError, ValueError) as error:
        print(json.dumps({"valid": False, "failure_reason": str(error)}))
        return 1
    print(result.model_dump_json(indent=2))
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
