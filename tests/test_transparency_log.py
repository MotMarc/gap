import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"
sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.core.repositories import transparency_log_repository  # noqa: E402
from app.core.transparency_log_config import (  # noqa: E402
    REFERENCE_TRANSPARENCY_LOG,
    TRUSTED_TRANSPARENCY_LOGS,
)
from app.crypto.merkle import (  # noqa: E402
    calculate_merkle_root,
    generate_consistency_proof,
    generate_inclusion_proof,
    hash_empty_tree,
    hash_leaf,
    hash_node,
    verify_consistency_proof,
    verify_inclusion_proof,
)
from app.domain.transparency_log import (  # noqa: E402
    TransparencyLogOperator,
    TransparencyLogSigningKey,
)
from app.services.transparency_log_repository import (  # noqa: E402
    TransparencyLogRepository,
    TransparencyLogRepositoryError,
)
from app.services.transparency_log_service import (  # noqa: E402
    create_signed_tree_head,
    verify_signed_tree_head_details,
)
from app.services.transparency_verification_service import verify_inclusion  # noqa: E402


def test_log_operator_requires_one_active_key() -> None:
    key = REFERENCE_TRANSPARENCY_LOG.active_signing_key
    with pytest.raises(ValueError):
        TransparencyLogOperator("log", "Log", key.key_id, (key, key))


def test_revoked_log_key_rejects_tree_head() -> None:
    head = transparency_log_repository.latest_tree_head()
    active = REFERENCE_TRANSPARENCY_LOG.active_signing_key
    revoked = TransparencyLogSigningKey(
        key_id=active.key_id,
        status="revoked",
        public_key_path=active.public_key_path,
        created_at=active.created_at,
        revoked_at=datetime.now(timezone.utc),
        revocation_reason="compromised",
    )
    operator = object.__new__(TransparencyLogOperator)
    object.__setattr__(operator, "log_id", REFERENCE_TRANSPARENCY_LOG.log_id)
    object.__setattr__(operator, "log_name", REFERENCE_TRANSPARENCY_LOG.log_name)
    object.__setattr__(operator, "active_key_id", active.key_id)
    object.__setattr__(operator, "signing_keys", (revoked,))
    result = verify_signed_tree_head_details(head, {operator.log_id: operator})
    assert result.valid is False
    assert result.failure_reason == "revoked-log-key"


def test_merkle_hash_vectors_and_tree_shape() -> None:
    assert hash_empty_tree() == hashlib.sha256(b"").digest()
    leaves = [hash_leaf(value) for value in (b"a", b"b", b"c")]
    assert calculate_merkle_root(leaves[:1]) == leaves[0]
    assert calculate_merkle_root(leaves[:2]) == hash_node(leaves[0], leaves[1])
    assert calculate_merkle_root(leaves) == hash_node(
        hash_node(leaves[0], leaves[1]), leaves[2]
    )


@pytest.mark.parametrize("size", range(1, 10))
def test_inclusion_proofs_validate_for_every_leaf(size: int) -> None:
    leaves = [hash_leaf(str(index).encode()) for index in range(size)]
    root = calculate_merkle_root(leaves)
    for index, leaf in enumerate(leaves):
        proof = generate_inclusion_proof(leaves, index)
        assert verify_inclusion_proof(leaf, index, size, proof, root)
        if proof:
            tampered = [*proof]
            tampered[0] = b"\0" * 32
            assert not verify_inclusion_proof(leaf, index, size, tampered, root)


@pytest.mark.parametrize(
    ("old_size", "new_size"),
    [(0, 1), (1, 2), (1, 3), (2, 3), (2, 8), (3, 8), (7, 8), (8, 8)],
)
def test_consistency_proofs_validate(old_size: int, new_size: int) -> None:
    leaves = [hash_leaf(str(index).encode()) for index in range(new_size)]
    proof = generate_consistency_proof(leaves, old_size)
    assert verify_consistency_proof(
        old_size,
        new_size,
        calculate_merkle_root(leaves[:old_size]),
        calculate_merkle_root(leaves),
        proof,
    )
    if proof:
        tampered = [*proof]
        tampered[0] = b"\0" * 32
        assert not verify_consistency_proof(
            old_size,
            new_size,
            calculate_merkle_root(leaves[:old_size]),
            calculate_merkle_root(leaves),
            tampered,
        )


def test_repository_entries_and_tree_heads_are_immutable() -> None:
    entry = transparency_log_repository.get_by_index(0)
    repository = TransparencyLogRepository(REFERENCE_TRANSPARENCY_LOG)
    repository.append(entry)
    with pytest.raises(TransparencyLogRepositoryError, match="duplicate"):
        repository.append(entry)
    head = create_signed_tree_head(
        REFERENCE_TRANSPARENCY_LOG, 1, repository.current_root()
    )
    repository.store_tree_head(head)
    with pytest.raises(TransparencyLogRepositoryError, match="duplicate"):
        repository.store_tree_head(head)


def test_current_entry_has_valid_signed_inclusion() -> None:
    entry = transparency_log_repository.get_by_index(0)
    head = transparency_log_repository.latest_tree_head()
    proof = transparency_log_repository.inclusion_proof(
        entry.entry_id, head.payload.tree_size
    )
    result = verify_inclusion(entry, head, proof, TRUSTED_TRANSPARENCY_LOGS)
    assert result.valid is True
    tampered = entry.model_copy(update={"object_digest": "0" * 64})
    assert (
        verify_inclusion(tampered, head, proof, TRUSTED_TRANSPARENCY_LOGS).valid
        is False
    )


def test_signed_tree_head_signature_covers_root_and_size() -> None:
    head = transparency_log_repository.latest_tree_head()
    assert verify_signed_tree_head_details(head, TRUSTED_TRANSPARENCY_LOGS).valid
    changed_payload = head.payload.model_copy(update={"root_hash": "0" * 64})
    changed = head.model_copy(update={"payload": changed_payload})
    assert not verify_signed_tree_head_details(changed, TRUSTED_TRANSPARENCY_LOGS).valid
