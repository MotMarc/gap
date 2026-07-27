from app.core.transparency_log_config import TRUSTED_TRANSPARENCY_LOGS
from app.crypto.canonical_json import canonicalise_model
from app.crypto.merkle import (
    verify_consistency_proof,
    verify_inclusion_proof,
    hash_leaf,
)
from app.schemas.transparency_proof import (
    ConsistencyVerificationResult,
    InclusionVerificationResult,
)
from app.services.transparency_log_service import verify_signed_tree_head_details


def _decode_hashes(values):
    try:
        decoded = [bytes.fromhex(item) for item in values]
    except ValueError:
        return None
    return decoded if all(len(item) == 32 for item in decoded) else None


def verify_inclusion(
    entry, tree_head, proof, trusted_logs=TRUSTED_TRANSPARENCY_LOGS
) -> InclusionVerificationResult:
    if proof.log_id != tree_head.payload.log_id:
        return InclusionVerificationResult(
            valid=False, failure_reason="log-id-mismatch"
        )
    if proof.tree_size != tree_head.payload.tree_size:
        return InclusionVerificationResult(
            valid=False, failure_reason="tree-size-mismatch"
        )
    if proof.root_hash != tree_head.payload.root_hash:
        return InclusionVerificationResult(
            valid=False, failure_reason="root-hash-mismatch"
        )
    if proof.entry_id != entry.entry_id:
        return InclusionVerificationResult(
            valid=False, failure_reason="transparency-object-mismatch"
        )
    tree_result = verify_signed_tree_head_details(tree_head, trusted_logs)
    if not tree_result.valid:
        return InclusionVerificationResult(
            valid=False, failure_reason=tree_result.failure_reason
        )
    leaf = hash_leaf(canonicalise_model(entry))
    if leaf.hex() != proof.leaf_hash:
        return InclusionVerificationResult(
            valid=False, failure_reason="invalid-leaf-hash"
        )
    path = _decode_hashes(proof.audit_path)
    if path is None:
        return InclusionVerificationResult(
            valid=False, failure_reason="malformed-audit-path"
        )
    valid = verify_inclusion_proof(
        leaf,
        proof.leaf_index,
        proof.tree_size,
        path,
        bytes.fromhex(proof.root_hash),
    )
    return InclusionVerificationResult(
        valid=valid,
        entry_id=entry.entry_id,
        tree_head_id=tree_head.payload.tree_head_id,
        failure_reason=None if valid else "inclusion-proof-failed",
    )


def verify_consistency(
    old_tree_head, new_tree_head, proof, trusted_logs=TRUSTED_TRANSPARENCY_LOGS
):
    old_result = verify_signed_tree_head_details(old_tree_head, trusted_logs)
    new_result = verify_signed_tree_head_details(new_tree_head, trusted_logs)
    if not old_result.valid or not new_result.valid:
        return ConsistencyVerificationResult(
            valid=False,
            failure_reason=(old_result.failure_reason or new_result.failure_reason),
        )
    old, new = old_tree_head.payload, new_tree_head.payload
    if old.log_id != new.log_id or proof.log_id != old.log_id:
        return ConsistencyVerificationResult(
            valid=False, failure_reason="log-id-mismatch"
        )
    if old.tree_size > new.tree_size:
        return ConsistencyVerificationResult(
            valid=False, failure_reason="tree-size-regression"
        )
    if old.tree_size == new.tree_size and old.root_hash != new.root_hash:
        return ConsistencyVerificationResult(
            valid=False,
            split_view=True,
            failure_reason="split-view-detected",
        )
    if (
        proof.old_tree_size != old.tree_size
        or proof.new_tree_size != new.tree_size
        or proof.old_root_hash != old.root_hash
        or proof.new_root_hash != new.root_hash
    ):
        return ConsistencyVerificationResult(
            valid=False, failure_reason="root-hash-mismatch"
        )
    path = _decode_hashes(proof.consistency_path)
    if path is None:
        return ConsistencyVerificationResult(
            valid=False, failure_reason="malformed-consistency-path"
        )
    valid = verify_consistency_proof(
        old.tree_size,
        new.tree_size,
        bytes.fromhex(old.root_hash),
        bytes.fromhex(new.root_hash),
        path,
    )
    return ConsistencyVerificationResult(
        valid=valid,
        append_only=valid,
        failure_reason=None if valid else "consistency-proof-failed",
    )
