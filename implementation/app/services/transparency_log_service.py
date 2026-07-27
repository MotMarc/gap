from binascii import Error as Base64DecodeError
from datetime import datetime, timezone
from uuid import uuid4

from app.crypto.canonical_json import canonicalise_model
from app.crypto.provider_keys import decode_public_key, load_private_key
from app.crypto.signatures import sign_payload, verify_payload
from app.domain.transparency_log import TransparencyLogOperator
from app.schemas.signed_tree_head import (
    SignedTreeHead,
    TreeHeadPayload,
    TreeHeadProof,
    TreeHeadVerificationResult,
)
from app.services.transparency_log_identity_service import (
    create_transparency_log_identity_document,
)


def create_signed_tree_head(
    operator: TransparencyLogOperator,
    tree_size: int,
    root_hash: str,
    timestamp: datetime | None = None,
    tree_head_id: str | None = None,
) -> SignedTreeHead:
    key = operator.active_signing_key
    if not key.can_sign_tree_heads:
        raise ValueError("Only an active log key may sign a tree head.")
    payload = TreeHeadPayload(
        tree_head_id=tree_head_id or f"gap-tree-head-{uuid4()}",
        log_id=operator.log_id,
        log_name=operator.log_name,
        tree_size=tree_size,
        root_hash=root_hash,
        timestamp=timestamp or datetime.now(timezone.utc),
    )
    signature = sign_payload(
        canonicalise_model(payload), load_private_key(key.private_key_path)
    )
    return SignedTreeHead(
        payload=payload,
        proof=TreeHeadProof(key_id=key.key_id, signature=signature),
    )


def verify_signed_tree_head_details(
    tree_head: SignedTreeHead,
    trusted_logs: dict[str, TransparencyLogOperator],
) -> TreeHeadVerificationResult:
    payload, proof = tree_head.payload, tree_head.proof
    base = dict(
        tree_head_id=payload.tree_head_id,
        log_id=payload.log_id,
        tree_size=payload.tree_size,
        root_hash=payload.root_hash,
        key_id=proof.key_id,
    )
    operator = trusted_logs.get(payload.log_id)
    if operator is None:
        return TreeHeadVerificationResult(
            valid=False, failure_reason="unknown-transparency-log", **base
        )
    base["log_trusted"] = True
    if payload.log_name != operator.log_name:
        return TreeHeadVerificationResult(
            valid=False, failure_reason="log-id-mismatch", **base
        )
    try:
        key = operator.get_signing_key(proof.key_id)
    except LookupError:
        return TreeHeadVerificationResult(
            valid=False, failure_reason="unknown-log-key", **base
        )
    base["key_status"] = key.status
    if key.status == "revoked":
        return TreeHeadVerificationResult(
            valid=False, failure_reason="revoked-log-key", **base
        )
    try:
        identity = create_transparency_log_identity_document(operator)
        published = next(
            item for item in identity.signing_keys if item.key_id == key.key_id
        )
        public_key = decode_public_key(published.public_key)
        signature_valid = verify_payload(
            canonicalise_model(payload), proof.signature, public_key
        )
    except (ValueError, Base64DecodeError, StopIteration):
        return TreeHeadVerificationResult(
            valid=False, failure_reason="invalid-log-public-key", **base
        )
    if not signature_valid:
        return TreeHeadVerificationResult(
            valid=False,
            signature_valid=False,
            failure_reason="invalid-tree-head-signature",
            **base,
        )
    return TreeHeadVerificationResult(valid=True, signature_valid=True, **base)


def verify_signed_tree_head(
    tree_head: SignedTreeHead, trusted_logs: dict[str, TransparencyLogOperator]
) -> bool:
    return verify_signed_tree_head_details(tree_head, trusted_logs).valid
