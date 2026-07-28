from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.checkpoint_gossip import CheckpointGossipPackage, GossipMonitorResult
from app.services.transparency_log_service import verify_signed_tree_head_details
from app.services.transparency_verification_service import verify_consistency
from app.services.witness_quorum_service import evaluate_witness_quorum


def create_checkpoint_gossip_package(
    signed_tree_head,
    witness_statements,
    *,
    previous_signed_tree_head=None,
    consistency_proof_to_previous=None,
    exported_at=None,
    gossip_id=None,
):
    return CheckpointGossipPackage(
        gossip_id=gossip_id or f"gap-gossip-{uuid4()}",
        exported_at=exported_at or datetime.now(timezone.utc),
        signed_tree_head=signed_tree_head,
        witness_statements=tuple(witness_statements),
        previous_signed_tree_head=previous_signed_tree_head,
        consistency_proof_to_previous=consistency_proof_to_previous,
    )


def verify_checkpoint_gossip_package(
    package,
    trusted_logs,
    witness_repository,
    policy,
    known_packages=(),
    now=None,
):
    current = package.signed_tree_head.payload
    tree_result = verify_signed_tree_head_details(
        package.signed_tree_head, trusted_logs
    )
    if not tree_result.valid:
        return GossipMonitorResult(
            checkpoint_gossip_consistent=False,
            log_id=current.log_id,
            tree_head_id=current.tree_head_id,
            tree_size=current.tree_size,
            root_hash=current.root_hash,
            failure_reason=tree_result.failure_reason,
        )
    relevant = [
        item
        for item in known_packages
        if item.signed_tree_head.payload.log_id == current.log_id
    ]
    conflicts = [
        item.signed_tree_head.payload.tree_head_id
        for item in relevant
        if item.signed_tree_head.payload.tree_size == current.tree_size
        and item.signed_tree_head.payload.root_hash != current.root_hash
    ]
    all_statements = list(package.witness_statements)
    for item in relevant:
        all_statements.extend(item.witness_statements)
    equivocators = sorted(
        {
            statement.payload.witness_id
            for statement in all_statements
            if len(
                {
                    other.payload.root_hash
                    for other in all_statements
                    if other.payload.witness_id == statement.payload.witness_id
                    and other.payload.log_id == statement.payload.log_id
                    and other.payload.tree_size == statement.payload.tree_size
                }
            )
            > 1
        }
    )
    largest_known = max(
        (item.signed_tree_head.payload.tree_size for item in relevant),
        default=-1,
    )
    rollback = current.tree_size < largest_known
    consistency_proven = current.tree_size == 0
    consistency_unproven = False
    consistency_failure = None
    if package.previous_signed_tree_head is not None:
        if package.consistency_proof_to_previous is None:
            consistency_unproven = True
        else:
            result = verify_consistency(
                package.previous_signed_tree_head,
                package.signed_tree_head,
                package.consistency_proof_to_previous,
                trusted_logs,
            )
            consistency_proven = result.valid
            consistency_failure = result.failure_reason if not result.valid else None
    elif current.tree_size > 0 and relevant:
        consistency_unproven = True
    quorum = evaluate_witness_quorum(
        package.signed_tree_head,
        package.witness_statements,
        witness_repository,
        policy,
        now,
    )
    failure = None
    if conflicts:
        failure = "split-view-detected"
    elif equivocators:
        failure = "witness-equivocation-detected"
    elif rollback:
        failure = "log-rollback-detected"
    elif consistency_failure:
        failure = consistency_failure
    elif consistency_unproven:
        failure = "consistency-unproven"
    elif not quorum.quorum_met:
        failure = quorum.failure_reason
    return GossipMonitorResult(
        checkpoint_gossip_consistent=failure is None,
        split_view_detected=bool(conflicts),
        witness_equivocation_detected=bool(equivocators),
        rollback_detected=rollback,
        consistency_proven=consistency_proven,
        consistency_unproven=consistency_unproven,
        log_id=current.log_id,
        tree_head_id=current.tree_head_id,
        tree_size=current.tree_size,
        root_hash=current.root_hash,
        failure_reason=failure,
        conflicting_tree_head_ids=conflicts,
        equivocating_witness_ids=equivocators,
    )
