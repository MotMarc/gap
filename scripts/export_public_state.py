import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "implementation"))
from app.core.provider_config import provider_repository  # noqa: E402
from app.core.registry_authority_config import registry_authority_repository  # noqa: E402
from app.services.public_state_service import serialise_public_state  # noqa: E402
from gap_sdk.trust import save_trust_material  # noqa: E402


def serialise(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if hasattr(value, "__dataclass_fields__"):
        from dataclasses import asdict

        return asdict(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Export public verifiable GAP state.")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    state = serialise_public_state(provider_repository, registry_authority_repository)
    save_trust_material(
        json.loads(json.dumps(state, default=serialise)),
        args.output,
        overwrite=False,
    )
    print(f"export={args.output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
