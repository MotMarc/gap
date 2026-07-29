from __future__ import annotations

from datetime import datetime, timezone

from app.core.repositories import (
    checkpoint_gossip_repository,
    federation_bundle_repository,
    transparency_log_repository,
    trust_attestation_repository,
    trust_registry_repository,
    witness_statement_repository,
)
from app.core.transparency_log_config import REFERENCE_TRANSPARENCY_LOG
from app.core.transparency_witness_config import transparency_witness_repository
from app.core.version import APPLICATION_VERSION
from app.services.provider_identity_service import create_provider_identity_document
from app.services.registry_authority_identity_service import (
    create_registry_authority_identity_document,
)
from app.services.transparency_log_identity_service import (
    create_transparency_log_identity_document,
)
from app.services.transparency_witness_identity_service import (
    create_transparency_witness_identity_document,
)
from app.services.witness_quorum_service import WitnessQuorumPolicy


def serialise_public_state(
    provider_repository, registry_authority_repository, *, exported_at=None
) -> dict:
    heads = transparency_log_repository.list_tree_heads()
    entries = transparency_log_repository.list_entries()
    latest = heads[-1] if heads else None
    inclusion_proofs = (
        [
            transparency_log_repository.inclusion_proof(
                entry.entry_id, latest.payload.tree_size
            )
            for entry in entries[: latest.payload.tree_size]
        ]
        if latest
        else []
    )
    consistency_proofs = [
        transparency_log_repository.consistency_proof(
            old.payload.tree_size, new.payload.tree_size
        )
        for old, new in zip(heads, heads[1:], strict=False)
    ]
    policy = WitnessQuorumPolicy()
    return {
        "bundle_format": "gap-public-state-v2",
        "application_version": APPLICATION_VERSION,
        "exported_at": (exported_at or datetime.now(timezone.utc)),
        "supported_maximum_verification_level": "full",
        "local_authority_id": "gap-reference-registry",
        "providers": [
            create_provider_identity_document(item)
            for item in provider_repository.list_all()
        ],
        "registry_authorities": [
            create_registry_authority_identity_document(item)
            for item in registry_authority_repository.list_all()
        ],
        "trust_decisions": trust_registry_repository.list_all(),
        "trust_attestations": trust_attestation_repository.list_all(),
        "federation_bundles": federation_bundle_repository.list_all(),
        "transparency_log_identities": [
            create_transparency_log_identity_document(REFERENCE_TRANSPARENCY_LOG)
        ],
        "transparency_entries": entries,
        "signed_tree_heads": heads,
        "inclusion_proofs": inclusion_proofs,
        "consistency_proofs": consistency_proofs,
        "witness_identities": [
            create_transparency_witness_identity_document(item)
            for item in transparency_witness_repository.list_trusted_witnesses()
        ],
        "witness_statements": witness_statement_repository.list_all(),
        "witness_quorum_policy": {
            "required_witness_count": policy.required_witness_count,
            "required_witness_ids": sorted(policy.required_witness_ids),
            "allow_retired_keys_for_historical_checkpoints": (
                policy.allow_retired_keys_for_historical_checkpoints
            ),
            "maximum_statement_age_seconds": int(
                policy.maximum_statement_age.total_seconds()
            ),
        },
        "gossip_observations": checkpoint_gossip_repository.list_all(),
        "private_data_included": False,
    }
