from dataclasses import dataclass
from datetime import timedelta

from pydantic import BaseModel

from app.services.transparency_witness_service import (
    MAXIMUM_STATEMENT_AGE,
    verify_witness_statement,
)


@dataclass(frozen=True, slots=True)
class WitnessQuorumPolicy:
    required_witness_count: int = 1
    required_witness_ids: frozenset[str] = frozenset()
    allow_retired_keys_for_historical_checkpoints: bool = True
    maximum_statement_age: timedelta = MAXIMUM_STATEMENT_AGE

    def __post_init__(self):
        if self.required_witness_count < 1:
            raise ValueError("Witness quorum must require at least one witness.")


class WitnessQuorumResult(BaseModel):
    quorum_met: bool
    required_witness_count: int
    valid_witness_count: int
    valid_witness_ids: list[str]
    invalid_witness_ids: list[str]
    missing_required_witness_ids: list[str]
    stale_witness_ids: list[str]
    revoked_witness_ids: list[str]
    tree_head_id: str
    tree_size: int
    root_hash: str
    failure_reason: str | None = None
    witness_results: list[dict]


def evaluate_witness_quorum(
    tree_head, statements, witness_repository, policy=WitnessQuorumPolicy(), now=None
):
    results = [
        verify_witness_statement(
            item,
            tree_head,
            witness_repository,
            now=now,
            maximum_statement_age=policy.maximum_statement_age,
        )
        for item in statements
    ]
    by_witness = {}
    equivocation = set()
    for statement, result in zip(statements, results, strict=True):
        witness_id = statement.payload.witness_id
        roots = {
            item.payload.root_hash
            for item in statements
            if item.payload.witness_id == witness_id
            and item.payload.log_id == statement.payload.log_id
            and item.payload.tree_size == statement.payload.tree_size
        }
        if len(roots) > 1:
            equivocation.add(witness_id)
        if result.valid and witness_id not in by_witness:
            by_witness[witness_id] = result
    for witness_id in equivocation:
        by_witness.pop(witness_id, None)
    valid_ids = sorted(by_witness)
    missing = sorted(policy.required_witness_ids - set(valid_ids))
    stale = sorted(
        {
            result.witness_id
            for result in results
            if result.failure_reason == "witness-statement-stale" and result.witness_id
        }
    )
    revoked = sorted(
        {
            result.witness_id
            for result in results
            if result.failure_reason == "revoked-witness-key" and result.witness_id
        }
    )
    met = (
        len(valid_ids) >= policy.required_witness_count
        and not missing
        and not equivocation
    )
    reason = None
    if equivocation:
        reason = "witness-equivocation-detected"
    elif not statements:
        reason = "no-witness-statements"
    elif missing:
        reason = "required-witness-missing"
    elif len(valid_ids) < policy.required_witness_count:
        reason = "insufficient-witness-quorum"
    payload = tree_head.payload
    return WitnessQuorumResult(
        quorum_met=met,
        required_witness_count=policy.required_witness_count,
        valid_witness_count=len(valid_ids),
        valid_witness_ids=valid_ids,
        invalid_witness_ids=sorted(
            {
                result.witness_id
                for result in results
                if not result.valid and result.witness_id
            }
        ),
        missing_required_witness_ids=missing,
        stale_witness_ids=stale,
        revoked_witness_ids=revoked,
        tree_head_id=payload.tree_head_id,
        tree_size=payload.tree_size,
        root_hash=payload.root_hash,
        failure_reason=reason,
        witness_results=[item.model_dump(mode="json") for item in results],
    )
