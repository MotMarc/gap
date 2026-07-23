import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "implementation"))

from app.core.registry_authority_config import registry_authority_repository  # noqa: E402
from app.services.federation_bundle_repository import FederationBundleRepository  # noqa: E402
from app.services.federation_bundle_service import import_federation_bundle  # noqa: E402
from app.services.federation_file_service import (  # noqa: E402
    load_accepted_bundle_directory,
    read_bundle_file,
    write_bundle_atomically,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a GAP federation bundle.")
    parser.add_argument("bundle", type=Path)
    parser.add_argument(
        "--accepted-directory",
        type=Path,
        default=Path("runtime/federation/accepted"),
    )
    args = parser.parse_args()
    repository = FederationBundleRepository()
    load_accepted_bundle_directory(
        args.accepted_directory, registry_authority_repository, repository
    )
    try:
        bundle = read_bundle_file(args.bundle)
        result = import_federation_bundle(
            bundle, registry_authority_repository, repository
        )
        if not result.imported:
            print(result.verification.model_dump_json(indent=2))
            return 1
        safe_name = f"{bundle.payload.registry_authority_id}-{bundle.payload.sequence_number}.json"
        write_bundle_atomically(bundle, args.accepted_directory / safe_name)
    except (OSError, ValueError) as error:
        print(f"imported=false failure_reason={error}")
        return 1
    print(
        f"imported=true bundle_id={bundle.payload.bundle_id} "
        f"sequence={bundle.payload.sequence_number} "
        f"digest={result.verification.bundle_hash}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
