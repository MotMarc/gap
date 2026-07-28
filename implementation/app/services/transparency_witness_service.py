from binascii import Error as Base64DecodeError
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.crypto.canonical_json import canonicalise_model
from app.crypto.provider_keys import decode_public_key, load_private_key
from app.crypto.signatures import sign_payload, verify_payload
from app.schemas.witness_statement import (
    WitnessStatement,
    WitnessStatementPayload,
    WitnessStatementProof,
    WitnessStatementVerificationResult,
)
from app.services.transparency_log_service import verify_signed_tree_head_details
from app.services.transparency_verification_service import verify_consistency
from app.services.transparency_witness_identity_service import (
    create_transparency_witness_identity_document,
)


MAXIMUM_OBSERVATION_DELAY = timedelta(hours=24)
MAXIMUM_FUTURE_CLOCK_SKEW = timedelta(minutes=5)
MAXIMUM_STATEMENT_AGE = timedelta(days=30)


def issue_witness_statement(
    witness,
    signed_tree_head,
    log_identity_document,
    previous_signed_tree_head=None,
    consistency_proof=None,
    observed_at=None,
    statement_id=None,
    trusted_logs=None,
) -> WitnessStatement:
    now = observed_at or datetime.now(timezone.utc)
    if now.tzinfo is None or signed_tree_head.payload.timestamp.tzinfo is None:
        raise ValueError("naive-witness-timestamp")
    if signed_tree_head.payload.log_id != log_identity_document.log_id:
        raise ValueError("log-id-mismatch")
    logs = trusted_logs
    if logs is None:
        from app.core.transparency_log_config import TRUSTED_TRANSPARENCY_LOGS

        logs = TRUSTED_TRANSPARENCY_LOGS
    tree_result = verify_signed_tree_head_details(signed_tree_head, logs)
    if not tree_result.valid:
        raise ValueError(tree_result.failure_reason)
    if now < signed_tree_head.payload.timestamp - MAXIMUM_FUTURE_CLOCK_SKEW:
        raise ValueError("witness-observation-before-checkpoint")
    if now - signed_tree_head.payload.timestamp > MAXIMUM_OBSERVATION_DELAY:
        raise ValueError("witness-observation-too-late")
    reference_size = reference_root = None
    if previous_signed_tree_head is not None:
        old = previous_signed_tree_head.payload
        new = signed_tree_head.payload
        if old.tree_size > new.tree_size:
            raise ValueError("tree-size-regression")
        if old.tree_size == new.tree_size and old.root_hash != new.root_hash:
            raise ValueError("split-view-detected")
        if consistency_proof is None:
            raise ValueError("consistency-proof-missing")
        result = verify_consistency(
            previous_signed_tree_head, signed_tree_head, consistency_proof, logs
        )
        if not result.valid:
            raise ValueError(result.failure_reason or "consistency-proof-failed")
        reference_size, reference_root = old.tree_size, old.root_hash
    elif consistency_proof is not None:
        raise ValueError("consistency-reference-missing")
    key = witness.active_signing_key
    payload = WitnessStatementPayload(
        statement_id=statement_id or f"gap-witness-statement-{uuid4()}",
        witness_id=witness.witness_id,
        witness_name=witness.witness_name,
        log_id=signed_tree_head.payload.log_id,
        tree_head_id=signed_tree_head.payload.tree_head_id,
        tree_size=signed_tree_head.payload.tree_size,
        root_hash=signed_tree_head.payload.root_hash,
        tree_head_timestamp=signed_tree_head.payload.timestamp,
        observed_at=now,
        consistency_reference_tree_size=reference_size,
        consistency_reference_root_hash=reference_root,
    )
    return WitnessStatement(
        payload=payload,
        proof=WitnessStatementProof(
            key_id=key.key_id,
            signature=sign_payload(
                canonicalise_model(payload), load_private_key(key.private_key_path)
            ),
        ),
    )


def verify_witness_statement(
    statement,
    signed_tree_head,
    witness_repository,
    *,
    now=None,
    maximum_statement_age=MAXIMUM_STATEMENT_AGE,
) -> WitnessStatementVerificationResult:
    payload, proof = statement.payload, statement.proof
    base = dict(
        statement_id=payload.statement_id,
        witness_id=payload.witness_id,
        witness_key_id=proof.key_id,
        log_id=payload.log_id,
        tree_head_id=payload.tree_head_id,
        tree_size=payload.tree_size,
        root_hash=payload.root_hash,
    )
    try:
        witness = witness_repository.get(payload.witness_id)
    except LookupError:
        return WitnessStatementVerificationResult(
            valid=False, failure_reason="unknown-transparency-witness", **base
        )
    base["witness_trusted"] = True
    if payload.witness_name != witness.witness_name:
        return WitnessStatementVerificationResult(
            valid=False, failure_reason="witness-mismatch", **base
        )
    try:
        key = witness.get_signing_key(proof.key_id)
    except LookupError:
        return WitnessStatementVerificationResult(
            valid=False, failure_reason="unknown-witness-key", **base
        )
    base["witness_key_status"] = key.status
    if proof.type != "Ed25519":
        return WitnessStatementVerificationResult(
            valid=False, failure_reason="witness-algorithm-mismatch", **base
        )
    if key.status == "revoked":
        return WitnessStatementVerificationResult(
            valid=False, failure_reason="revoked-witness-key", **base
        )
    checkpoint = signed_tree_head.payload
    bindings = (
        ("log-id-mismatch", payload.log_id, checkpoint.log_id),
        ("tree-head-id-mismatch", payload.tree_head_id, checkpoint.tree_head_id),
        ("tree-size-mismatch", payload.tree_size, checkpoint.tree_size),
        ("root-hash-mismatch", payload.root_hash, checkpoint.root_hash),
        (
            "checkpoint-timestamp-mismatch",
            payload.tree_head_timestamp,
            checkpoint.timestamp,
        ),
    )
    for reason, actual, expected in bindings:
        if actual != expected:
            return WitnessStatementVerificationResult(
                valid=False, failure_reason=reason, **base
            )
    if payload.verification_outcome != "accepted":
        return WitnessStatementVerificationResult(
            valid=False, failure_reason="unsupported-verification-outcome", **base
        )
    if payload.observed_at < checkpoint.timestamp - MAXIMUM_FUTURE_CLOCK_SKEW:
        return WitnessStatementVerificationResult(
            valid=False,
            checkpoint_binding_valid=True,
            failure_reason="witness-observation-before-checkpoint",
            **base,
        )
    current = now or datetime.now(timezone.utc)
    fresh = (
        payload.observed_at <= current + MAXIMUM_FUTURE_CLOCK_SKEW
        and current - payload.observed_at <= maximum_statement_age
    )
    try:
        identity = create_transparency_witness_identity_document(witness)
        published = next(
            item for item in identity.signing_keys if item.key_id == key.key_id
        )
        signature_valid = verify_payload(
            canonicalise_model(payload),
            proof.signature,
            decode_public_key(published.public_key),
        )
    except (ValueError, Base64DecodeError, StopIteration):
        return WitnessStatementVerificationResult(
            valid=False,
            checkpoint_binding_valid=True,
            failure_reason="invalid-witness-public-key",
            **base,
        )
    if not signature_valid:
        return WitnessStatementVerificationResult(
            valid=False,
            checkpoint_binding_valid=True,
            failure_reason="invalid-witness-signature",
            **base,
        )
    if not fresh:
        return WitnessStatementVerificationResult(
            valid=False,
            statement_signature_valid=True,
            checkpoint_binding_valid=True,
            failure_reason="witness-statement-stale",
            **base,
        )
    return WitnessStatementVerificationResult(
        valid=True,
        statement_signature_valid=True,
        checkpoint_binding_valid=True,
        statement_fresh=True,
        **base,
    )
