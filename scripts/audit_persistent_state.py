import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "implementation"))
from app.core.repositories import (  # noqa: E402
    checkpoint_gossip_repository,
    transparency_log_repository,
    trust_attestation_repository,
    trust_registry_repository,
    witness_statement_repository,
)
from app.crypto.canonical_json import canonicalise_model  # noqa: E402
from app.crypto.merkle import calculate_merkle_root, hash_leaf  # noqa: E402
from app.database import HEAD_REVISION, current_revision  # noqa: E402
from app.core.repositories import database  # noqa: E402


def main() -> int:
    errors = []
    decisions = trust_registry_repository.list_all()
    if len({item.decision_id for item in decisions}) != len(decisions):
        errors.append("duplicate trust decision ID")
    for provider_id in {item.provider_id for item in decisions}:
        history = [item for item in decisions if item.provider_id == provider_id]
        if history != sorted(history, key=lambda item: item.decided_at):
            errors.append(f"trust chronology invalid: {provider_id}")
    decision_ids = {item.decision_id for item in decisions}
    for attestation in trust_attestation_repository.list_all():
        if attestation.payload.decision_id not in decision_ids:
            errors.append(f"orphaned attestation: {attestation.payload.attestation_id}")
    entries = transparency_log_repository.list_entries()
    root = calculate_merkle_root(
        [hash_leaf(canonicalise_model(item)) for item in entries]
    ).hex()
    if root != transparency_log_repository.current_root():
        errors.append("Merkle root mismatch")
    for head in transparency_log_repository.list_tree_heads():
        if head.payload.tree_size > len(entries):
            errors.append(f"tree head exceeds log: {head.payload.tree_head_id}")
    if database is not None and current_revision(database.engine) != HEAD_REVISION:
        errors.append("database migration is not at head")
    print(
        f"decisions={len(decisions)} entries={len(entries)} "
        f"tree_heads={len(transparency_log_repository.list_tree_heads())} "
        f"witness_statements={len(witness_statement_repository.list_all())} "
        f"gossip_observations={len(checkpoint_gossip_repository.list_all())} "
        f"root={root} errors={len(errors)}"
    )
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
