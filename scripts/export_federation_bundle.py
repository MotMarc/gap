import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "implementation"))

from app.core.registry_authority_config import (  # noqa: E402
    REFERENCE_REGISTRY_AUTHORITY,
)
from app.core.repositories import trust_attestation_repository  # noqa: E402
from app.services.federation_bundle_service import (  # noqa: E402
    calculate_bundle_digest,
    issue_federation_bundle,
)
from app.services.federation_file_service import (  # noqa: E402
    read_bundle_file,
    write_bundle_atomically,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a signed GAP federation bundle."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--previous-bundle", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--valid-days", type=int, default=7)
    args = parser.parse_args()
    if not 1 <= args.valid_days <= 30:
        parser.error("--valid-days must be between 1 and 30")
    previous = read_bundle_file(args.previous_bundle) if args.previous_bundle else None
    sequence = previous.payload.sequence_number + 1 if previous else 1
    previous_hash = calculate_bundle_digest(previous) if previous else None
    now = datetime.now(timezone.utc)
    current = {}
    for attestation in trust_attestation_repository.list_all():
        current[attestation.payload.provider_id] = attestation
    bundle = issue_federation_bundle(
        REFERENCE_REGISTRY_AUTHORITY,
        current.values(),
        sequence,
        now,
        now + timedelta(days=args.valid_days),
        previous_hash,
    )
    write_bundle_atomically(bundle, args.output, args.overwrite)
    print(
        f"bundle_id={bundle.payload.bundle_id} sequence={sequence} "
        f"authority={bundle.payload.registry_authority_id} "
        f"expires_at={bundle.payload.expires_at.isoformat()} "
        f"digest={calculate_bundle_digest(bundle)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
