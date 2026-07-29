from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from pydantic import TypeAdapter

from app.domain.provider_trust import ProviderTrustDecision
from app.schemas.checkpoint_gossip import CheckpointGossipPackage
from app.schemas.federation_bundle import FederationBundle
from app.schemas.provider_identity import ProviderIdentityDocument
from app.schemas.registry_authority import RegistryAuthorityIdentityDocument
from app.schemas.signed_tree_head import SignedTreeHead
from app.schemas.transparency_entry import TransparencyLogEntry
from app.schemas.transparency_log import TransparencyLogIdentityDocument
from app.schemas.transparency_witness import TransparencyWitnessIdentityDocument
from app.schemas.trust_attestation import TrustDecisionAttestation
from app.schemas.witness_statement import WitnessStatement
from app.services.checkpoint_gossip_service import verify_checkpoint_gossip_package
from app.services.federated_trust_service import FederatedTrustService
from app.services.federation_bundle_repository import FederationBundleRepository
from app.services.federation_bundle_service import verify_federation_bundle
from app.services.provider_application_repository import ProviderApplicationRepository
from app.services.transparency_log_repository import TransparencyLogRepository
from app.services.trust_attestation_repository import TrustAttestationRepository
from app.services.trust_registry_repository import TrustRegistryRepository
from app.services.trust_registry_service import TrustRegistryService
from app.services.verification_service import verify_generation_credential_details
from app.services.witness_quorum_service import (
    WitnessQuorumPolicy,
    evaluate_witness_quorum,
)


def _time(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class _IdentityObject:
    def __init__(self, document, *, kind: str):
        self.identity_document = document
        if kind == "authority":
            self.authority_id = document.authority_id
            self.authority_name = document.authority_name
            self.active_key_id = document.active_key_id
            self.signing_keys = tuple(document.keys)
        elif kind == "log":
            self.log_id = document.log_id
            self.log_name = document.log_name
            self.active_key_id = document.active_key_id
            self.signing_keys = tuple(document.signing_keys)
        else:
            self.witness_id = document.witness_id
            self.witness_name = document.witness_name
            self.active_key_id = document.active_key_id
            self.signing_keys = tuple(document.signing_keys)

    def get_signing_key(self, key_id):
        key = next((item for item in self.signing_keys if item.key_id == key_id), None)
        if key is None:
            raise LookupError(key_id)
        return key


class _IdentityRepository:
    def __init__(self, objects, id_field):
        self.objects = {getattr(item, id_field): item for item in objects}
        self.id_field = id_field

    def get(self, object_id):
        try:
            return self.objects[object_id]
        except KeyError as exc:
            raise LookupError(object_id) from exc

    def list_all(self):
        return list(self.objects.values())

    def list_trusted_witnesses(self):
        return self.list_all()


def evaluate_offline_full(credential, state: dict, *, now=None) -> dict:
    current = now or datetime.now(timezone.utc)
    providers = [
        ProviderIdentityDocument.model_validate(item)
        for item in state.get("providers", [])
    ]
    provider = next(
        (
            item
            for item in providers
            if item.provider_id == credential.payload.provider.provider_id
        ),
        None,
    )
    cryptographic = (
        verify_generation_credential_details(credential, provider)
        if provider is not None
        else SimpleNamespace(valid=False, failure_reason="unknown-provider")
    )

    authorities = [
        _IdentityObject(
            RegistryAuthorityIdentityDocument.model_validate(item), kind="authority"
        )
        for item in state.get("registry_authorities", [])
    ]
    authority_repository = _IdentityRepository(authorities, "authority_id")
    decisions = [
        ProviderTrustDecision(
            decision_id=item["decision_id"],
            provider_id=item["provider_id"],
            status=item["status"],
            authority=item["authority"],
            reason=item["reason"],
            decided_at=_time(item["decided_at"]),
        )
        for item in state.get("trust_decisions", [])
    ]
    trust_repository = TrustRegistryRepository(decisions)
    attestations = [
        TrustDecisionAttestation.model_validate(item)
        for item in state.get("trust_attestations", [])
    ]
    attestation_repository = TrustAttestationRepository(attestations)

    log_objects = [
        _IdentityObject(
            TransparencyLogIdentityDocument.model_validate(item), kind="log"
        )
        for item in state.get("transparency_log_identities", [])
    ]
    trusted_logs = {item.log_id: item for item in log_objects}
    if not log_objects:
        return _incomplete(cryptographic, "missing-transparency-log-identity")
    transparency_repository = TransparencyLogRepository(log_objects[0])
    entry_adapter = TypeAdapter(TransparencyLogEntry)
    try:
        for item in state.get("transparency_entries", []):
            transparency_repository.append(entry_adapter.validate_python(item))
        for item in state.get("signed_tree_heads", []):
            transparency_repository.store_tree_head(SignedTreeHead.model_validate(item))
    except ValueError as exc:
        return _incomplete(cryptographic, str(exc))

    bundles = FederationBundleRepository()
    for raw in sorted(
        state.get("federation_bundles", []),
        key=lambda item: (
            item["payload"]["registry_authority_id"],
            item["payload"]["sequence_number"],
        ),
    ):
        bundle = FederationBundle.model_validate(raw)
        result = verify_federation_bundle(
            bundle, authority_repository, bundles, current
        )
        if not result.valid:
            return _incomplete(cryptographic, result.failure_reason)
        bundles.add_verified(bundle)

    local_authority_id = state.get("local_authority_id")
    local_service = TrustRegistryService(
        trust_repository,
        ProviderApplicationRepository(),
        authority_repository,
        attestation_repository,
        local_authority_id,
        transparency_repository,
    )
    federation_service = FederatedTrustService(
        local_service,
        authority_repository,
        bundles,
        local_authority_id,
        transparency_repository,
        trusted_logs,
    )
    federation = federation_service.evaluate(
        credential.payload.provider.provider_id, current
    )
    transparent = [
        source
        for source in federation.authority_sources
        if source.transparency_verified
    ]
    source = transparent[0] if transparent else None
    tree_head = (
        transparency_repository.get_tree_head(source.transparency_tree_head_id)
        if source and source.transparency_tree_head_id
        else None
    )

    witnesses = [
        _IdentityObject(
            TransparencyWitnessIdentityDocument.model_validate(item), kind="witness"
        )
        for item in state.get("witness_identities", [])
    ]
    witness_repository = _IdentityRepository(witnesses, "witness_id")
    statements = [
        WitnessStatement.model_validate(item)
        for item in state.get("witness_statements", [])
    ]
    policy_data = state.get("witness_quorum_policy", {})
    policy = WitnessQuorumPolicy(
        required_witness_count=policy_data.get("required_witness_count", 1),
        required_witness_ids=frozenset(policy_data.get("required_witness_ids", [])),
        allow_retired_keys_for_historical_checkpoints=policy_data.get(
            "allow_retired_keys_for_historical_checkpoints", True
        ),
        maximum_statement_age=timedelta(
            seconds=policy_data.get("maximum_statement_age_seconds", 30 * 24 * 60 * 60)
        ),
    )
    quorum = (
        evaluate_witness_quorum(
            tree_head,
            [
                item
                for item in statements
                if item.payload.tree_head_id == tree_head.payload.tree_head_id
            ],
            witness_repository,
            policy,
            current,
        )
        if tree_head
        else None
    )
    packages = [
        CheckpointGossipPackage.model_validate(item)
        for item in state.get("gossip_observations", [])
    ]
    matching = next(
        (
            item
            for item in reversed(packages)
            if tree_head
            and item.signed_tree_head.payload.tree_head_id
            == tree_head.payload.tree_head_id
        ),
        None,
    )
    gossip = (
        verify_checkpoint_gossip_package(
            matching,
            trusted_logs,
            witness_repository,
            policy,
            [item for item in packages if item.gossip_id != matching.gossip_id],
            current,
        )
        if matching
        else SimpleNamespace(
            checkpoint_gossip_consistent=False,
            split_view_detected=False,
            witness_equivocation_detected=False,
            rollback_detected=False,
            failure_reason="no-gossip-observations",
        )
    )
    flags = {
        "cryptographic_valid": cryptographic.valid,
        "provider_trusted": federation.trusted,
        "federation_state_valid": not federation.federation_conflict,
        "transparency_verified": bool(source),
        "witness_quorum_met": bool(quorum and quorum.quorum_met),
        "checkpoint_gossip_consistent": gossip.checkpoint_gossip_consistent,
        "federation_conflict": federation.federation_conflict,
        "split_view_detected": gossip.split_view_detected,
        "witness_equivocation_detected": gossip.witness_equivocation_detected,
        "rollback_detected": gossip.rollback_detected,
    }
    flags["valid"] = (
        flags["cryptographic_valid"]
        and flags["provider_trusted"]
        and flags["federation_state_valid"]
        and flags["transparency_verified"]
        and flags["witness_quorum_met"]
        and flags["checkpoint_gossip_consistent"]
        and not flags["federation_conflict"]
        and not flags["split_view_detected"]
        and not flags["witness_equivocation_detected"]
        and not flags["rollback_detected"]
    )
    flags["failure_reason"] = (
        None
        if flags["valid"]
        else cryptographic.failure_reason
        or federation.failure_reason
        or (quorum.failure_reason if quorum else "missing-witness-evidence")
        or gossip.failure_reason
    )
    return flags


def _incomplete(cryptographic, reason):
    return {
        "valid": False,
        "cryptographic_valid": cryptographic.valid,
        "provider_trusted": False,
        "federation_state_valid": False,
        "transparency_verified": False,
        "witness_quorum_met": False,
        "checkpoint_gossip_consistent": False,
        "federation_conflict": False,
        "split_view_detected": False,
        "witness_equivocation_detected": False,
        "rollback_detected": False,
        "incomplete": True,
        "failure_reason": reason,
    }
