"""RFC-6962-shaped SHA-256 Merkle tree with GAP canonical leaves."""

import hashlib


HASH_SIZE = 32


def hash_empty_tree() -> bytes:
    return hashlib.sha256(b"").digest()


def hash_leaf(canonical_entry_bytes: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + canonical_entry_bytes).digest()


def hash_node(left: bytes, right: bytes) -> bytes:
    if len(left) != HASH_SIZE or len(right) != HASH_SIZE:
        raise ValueError("Merkle node hashes must be 32 bytes.")
    return hashlib.sha256(b"\x01" + left + right).digest()


def _split(size: int) -> int:
    return 1 << (size - 1).bit_length() - 1


def calculate_merkle_root(leaves: list[bytes] | tuple[bytes, ...]) -> bytes:
    if not leaves:
        return hash_empty_tree()
    if any(len(item) != HASH_SIZE for item in leaves):
        raise ValueError("Merkle leaves must be 32-byte hashes.")
    if len(leaves) == 1:
        return leaves[0]
    split = _split(len(leaves))
    return hash_node(
        calculate_merkle_root(leaves[:split]),
        calculate_merkle_root(leaves[split:]),
    )


def generate_inclusion_proof(
    leaves: list[bytes] | tuple[bytes, ...], leaf_index: int
) -> list[bytes]:
    if leaf_index < 0 or leaf_index >= len(leaves):
        raise ValueError("Invalid Merkle leaf index.")
    if len(leaves) == 1:
        return []
    split = _split(len(leaves))
    if leaf_index < split:
        return generate_inclusion_proof(leaves[:split], leaf_index) + [
            calculate_merkle_root(leaves[split:])
        ]
    return generate_inclusion_proof(leaves[split:], leaf_index - split) + [
        calculate_merkle_root(leaves[:split])
    ]


def verify_inclusion_proof(
    leaf_hash: bytes,
    leaf_index: int,
    tree_size: int,
    audit_path: list[bytes] | tuple[bytes, ...],
    expected_root: bytes,
) -> bool:
    if (
        len(leaf_hash) != HASH_SIZE
        or len(expected_root) != HASH_SIZE
        or tree_size <= 0
        or leaf_index < 0
        or leaf_index >= tree_size
        or any(len(item) != HASH_SIZE for item in audit_path)
    ):
        return False
    fn, sn, result = leaf_index, tree_size - 1, leaf_hash
    path_index = 0
    while sn:
        if path_index >= len(audit_path):
            return False
        sibling = audit_path[path_index]
        if fn & 1 or fn == sn:
            result = hash_node(sibling, result)
            while not (fn & 1) and fn:
                fn >>= 1
                sn >>= 1
        else:
            result = hash_node(result, sibling)
        fn >>= 1
        sn >>= 1
        path_index += 1
    return path_index == len(audit_path) and result == expected_root


def generate_consistency_proof(
    leaves: list[bytes] | tuple[bytes, ...], old_tree_size: int
) -> list[bytes]:
    new_size = len(leaves)
    if old_tree_size < 0 or old_tree_size > new_size:
        raise ValueError("Invalid consistency tree size.")
    if old_tree_size == 0 or old_tree_size == new_size:
        return []

    def subproof(start: int, size: int, old_size: int, complete: bool) -> list[bytes]:
        if old_size == size:
            return (
                []
                if complete
                else [calculate_merkle_root(leaves[start : start + size])]
            )
        split = _split(size)
        if old_size <= split:
            return subproof(start, split, old_size, complete) + [
                calculate_merkle_root(leaves[start + split : start + size])
            ]
        return subproof(start + split, size - split, old_size - split, False) + [
            calculate_merkle_root(leaves[start : start + split])
        ]

    return subproof(0, new_size, old_tree_size, True)


def verify_consistency_proof(
    old_size: int,
    new_size: int,
    old_root: bytes,
    new_root: bytes,
    proof: list[bytes] | tuple[bytes, ...],
) -> bool:
    if (
        old_size < 0
        or new_size < 0
        or old_size > new_size
        or len(old_root) != HASH_SIZE
        or len(new_root) != HASH_SIZE
        or any(len(item) != HASH_SIZE for item in proof)
    ):
        return False
    if old_size == 0:
        return old_root == hash_empty_tree() and not proof
    if old_size == new_size:
        return old_root == new_root and not proof
    fn, sn = old_size - 1, new_size - 1
    while fn & 1:
        fn >>= 1
        sn >>= 1
    index = 0
    if fn == 0:
        old_hash = new_hash = old_root
    else:
        if not proof:
            return False
        old_hash = new_hash = proof[0]
        index = 1
    while index < len(proof):
        node = proof[index]
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            old_hash = hash_node(node, old_hash)
            new_hash = hash_node(node, new_hash)
            while not (fn & 1) and fn:
                fn >>= 1
                sn >>= 1
        else:
            new_hash = hash_node(new_hash, node)
        fn >>= 1
        sn >>= 1
        index += 1
    return sn == 0 and old_hash == old_root and new_hash == new_root
