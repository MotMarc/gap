import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"
sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.crypto.provider_keys import (  # noqa: E402
    generate_provider_key_pair,
    save_private_key,
    save_public_key,
)
from app.domain.transparency_log import (  # noqa: E402
    TransparencyLogOperator,
    TransparencyLogSigningKey,
)
from app.domain.transparency_witness import (  # noqa: E402
    TransparencyWitness,
    TransparencyWitnessSigningKey,
)
from app.schemas.checkpoint_gossip import CheckpointGossipPackage  # noqa: E402
from app.services.checkpoint_gossip_service import (  # noqa: E402
    create_checkpoint_gossip_package,
    verify_checkpoint_gossip_package,
)
from app.services.transparency_log_identity_service import (  # noqa: E402
    create_transparency_log_identity_document,
)
from app.services.transparency_log_service import create_signed_tree_head  # noqa: E402
from app.services.transparency_witness_repository import (  # noqa: E402
    TransparencyWitnessRepository,
)
from app.services.transparency_witness_service import (  # noqa: E402
    issue_witness_statement,
    verify_witness_statement,
)
from app.services.witness_quorum_service import (  # noqa: E402
    WitnessQuorumPolicy,
    evaluate_witness_quorum,
)


def identities(tmp_path):
    now = datetime.now(timezone.utc)
    log_private, log_public = generate_provider_key_pair()
    witness_private, witness_public = generate_provider_key_pair()
    paths = {
        "lp": tmp_path / "log-private.key",
        "lu": tmp_path / "log-public.key",
        "wp": tmp_path / "witness-private.key",
        "wu": tmp_path / "witness-public.key",
    }
    save_private_key(log_private, paths["lp"])
    save_public_key(log_public, paths["lu"])
    save_private_key(witness_private, paths["wp"])
    save_public_key(witness_public, paths["wu"])
    log = TransparencyLogOperator(
        "test-log",
        "Test Log",
        "log-key",
        (
            TransparencyLogSigningKey(
                "log-key", "active", paths["lu"], now, paths["lp"]
            ),
        ),
    )
    witness = TransparencyWitness(
        "test-witness",
        "Test Witness",
        "witness-key",
        (
            TransparencyWitnessSigningKey(
                "witness-key", "active", paths["wu"], now, paths["wp"]
            ),
        ),
    )
    return now, log, witness


def signed_evidence(tmp_path):
    now, log, witness = identities(tmp_path)
    head = create_signed_tree_head(log, 1, "ab" * 32, now, "head-1")
    statement = issue_witness_statement(
        witness,
        head,
        create_transparency_log_identity_document(log),
        observed_at=now + timedelta(minutes=1),
        statement_id="statement-1",
        trusted_logs={log.log_id: log},
    )
    repository = TransparencyWitnessRepository((witness,))
    return now, log, witness, head, statement, repository


def test_valid_statement_exact_binding_and_quorum(tmp_path):
    now, _, _, head, statement, repository = signed_evidence(tmp_path)
    result = verify_witness_statement(
        statement, head, repository, now=now + timedelta(minutes=2)
    )
    assert result.valid is True
    quorum = evaluate_witness_quorum(
        head,
        [statement, statement],
        repository,
        WitnessQuorumPolicy(required_witness_count=1),
        now + timedelta(minutes=2),
    )
    assert quorum.quorum_met is True
    assert quorum.valid_witness_count == 1


def test_tampering_unknown_witness_and_stale_statement_fail(tmp_path):
    now, _, _, head, statement, repository = signed_evidence(tmp_path)
    tampered = statement.model_copy(
        update={
            "payload": statement.payload.model_copy(update={"root_hash": "cd" * 32})
        }
    )
    assert (
        verify_witness_statement(tampered, head, repository).failure_reason
        == "root-hash-mismatch"
    )
    assert (
        verify_witness_statement(
            statement,
            head,
            TransparencyWitnessRepository(),
        ).failure_reason
        == "unknown-transparency-witness"
    )
    stale = verify_witness_statement(
        statement, head, repository, now=now + timedelta(days=31)
    )
    assert stale.failure_reason == "witness-statement-stale"


def test_gossip_split_view_rollback_and_equivocation(tmp_path):
    now, log, witness, head, statement, repository = signed_evidence(tmp_path)
    package = create_checkpoint_gossip_package(
        head, [statement], exported_at=now + timedelta(minutes=2), gossip_id="g1"
    )
    healthy = verify_checkpoint_gossip_package(
        package,
        {log.log_id: log},
        repository,
        WitnessQuorumPolicy(),
        now=now + timedelta(minutes=3),
    )
    assert healthy.checkpoint_gossip_consistent is True

    conflicting_head = create_signed_tree_head(
        log, 1, "cd" * 32, now + timedelta(minutes=2), "head-2"
    )
    conflicting_statement = issue_witness_statement(
        witness,
        conflicting_head,
        create_transparency_log_identity_document(log),
        observed_at=now + timedelta(minutes=3),
        statement_id="statement-2",
        trusted_logs={log.log_id: log},
    )
    conflicting = create_checkpoint_gossip_package(
        conflicting_head,
        [conflicting_statement],
        exported_at=now + timedelta(minutes=4),
        gossip_id="g2",
    )
    result = verify_checkpoint_gossip_package(
        conflicting,
        {log.log_id: log},
        repository,
        WitnessQuorumPolicy(),
        [package],
        now + timedelta(minutes=5),
    )
    assert result.split_view_detected is True
    assert result.witness_equivocation_detected is True
    assert result.checkpoint_gossip_consistent is False

    larger_head = create_signed_tree_head(
        log, 2, "ef" * 32, now + timedelta(minutes=6), "head-3"
    )
    larger = CheckpointGossipPackage(
        gossip_id="g3",
        exported_at=now + timedelta(minutes=7),
        signed_tree_head=larger_head,
        witness_statements=(),
    )
    rollback = verify_checkpoint_gossip_package(
        package,
        {log.log_id: log},
        repository,
        WitnessQuorumPolicy(),
        [larger],
        now=now + timedelta(minutes=8),
    )
    assert rollback.rollback_detected is True


def test_witness_identity_lifecycle_rejects_invalid_active_key(tmp_path):
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        TransparencyWitnessSigningKey(
            "key", "active", tmp_path / "public", now, private_key_path=None
        )
