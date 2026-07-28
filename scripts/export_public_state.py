import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "implementation"))
from app.core.provider_config import provider_repository  # noqa: E402
from app.core.registry_authority_config import registry_authority_repository  # noqa: E402
from app.core.repositories import (  # noqa: E402
    checkpoint_gossip_repository,
    federation_bundle_repository,
    transparency_log_repository,
    trust_attestation_repository,
    trust_registry_repository,
    witness_statement_repository,
)
from app.services.provider_identity_service import create_provider_identity_document  # noqa: E402
from app.services.registry_authority_identity_service import (  # noqa: E402
    create_registry_authority_identity_document,
)


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
    state = {
        "providers": [
            serialise(create_provider_identity_document(item))
            for item in provider_repository.list_all()
        ],
        "registry_authorities": [
            serialise(create_registry_authority_identity_document(item))
            for item in registry_authority_repository.list_all()
        ],
        "trust_decisions": [
            serialise(item) for item in trust_registry_repository.list_all()
        ],
        "trust_attestations": [
            serialise(item) for item in trust_attestation_repository.list_all()
        ],
        "federation_bundles": [
            serialise(item) for item in federation_bundle_repository.list_all()
        ],
        "transparency_entries": [
            serialise(item) for item in transparency_log_repository.list_entries()
        ],
        "signed_tree_heads": [
            serialise(item) for item in transparency_log_repository.list_tree_heads()
        ],
        "witness_statements": [
            serialise(item) for item in witness_statement_repository.list_all()
        ],
        "gossip_observations": [
            serialise(item) for item in checkpoint_gossip_repository.list_all()
        ],
    }
    encoded = json.dumps(
        state, default=str, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    envelope = {
        "manifest": {
            "format": "gap-public-state-v1",
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "private_data_included": False,
        },
        "state": state,
    }
    args.output.write_text(
        json.dumps(envelope, default=str, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"export={args.output.name} sha256={envelope['manifest']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
