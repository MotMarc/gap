from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone

from pydantic import TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.crypto.canonical_json import canonicalise_model
from app.crypto.merkle import (
    calculate_merkle_root,
    generate_consistency_proof,
    generate_inclusion_proof,
    hash_leaf,
)
from app.domain.disclosure_audit_record import DisclosureAuditRecord
from app.domain.provider_application import ProviderOnboardingApplication
from app.domain.provider_attribution_record import ProviderAttributionRecord
from app.domain.provider_trust import ProviderTrustDecision
from app.schemas.checkpoint_gossip import CheckpointGossipPackage
from app.schemas.federation_bundle import FederationBundle
from app.schemas.signed_tree_head import SignedTreeHead
from app.schemas.transparency_entry import TransparencyLogEntry
from app.schemas.transparency_proof import ConsistencyProof, InclusionProof
from app.schemas.trust_attestation import TrustDecisionAttestation
from app.schemas.witness_statement import WitnessStatement
from app.services.attribution_repository import (
    AttributionRecordAlreadyExistsError,
    AttributionRecordNotFoundError,
)
from app.services.federation_bundle_repository import (
    FederationBundleNotFoundError,
    FederationBundleRepositoryError,
)
from app.services.federation_bundle_service import calculate_bundle_digest
from app.services.provider_application_repository import (
    DuplicateProviderApplicationError,
    ProviderApplicationNotFoundError,
)
from app.services.transparency_entry_service import validate_entry_digest
from app.services.transparency_log_repository import (
    TransparencyEntryNotFoundError,
    TransparencyLogRepositoryError,
    TransparencyTreeHeadNotFoundError,
)
from app.services.transparency_log_service import create_signed_tree_head
from app.services.trust_attestation_repository import (
    DuplicateTrustAttestationError,
    TrustAttestationNotFoundError,
)
from app.services.trust_registry_repository import DuplicateTrustDecisionError

from app.database.models import (
    AttributionRecordRow,
    DisclosureAuditRow,
    FederationBundleRow,
    GossipObservationRow,
    ProviderApplicationRow,
    SignedTreeHeadRow,
    TransparencyEntryRow,
    TrustAttestationRow,
    TrustDecisionRow,
    WitnessStatementRow,
)
from app.database.uow import CURRENT_SESSION


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _json_model(model) -> str:
    return json.dumps(
        model.model_dump(mode="json", exclude_none=True),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


class SqlRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def _run(self, operation, integrity_error):
        ambient = CURRENT_SESSION.get()
        if ambient is not None:
            try:
                result = operation(ambient)
                ambient.flush()
                return result
            except IntegrityError as error:
                raise integrity_error from error
        session = self.session_factory()
        try:
            result = operation(session)
            session.commit()
            return result
        except IntegrityError as error:
            session.rollback()
            raise integrity_error from error
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def _read_session(self):
        """Reuse the transaction session so reads observe pending writes."""
        ambient = CURRENT_SESSION.get()
        if ambient is not None:
            yield ambient
            return
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()


class SqlProviderApplicationRepository(SqlRepository):
    def add(self, application):
        def operation(session):
            if application.is_active and self._active(session, application.provider_id):
                raise DuplicateProviderApplicationError(
                    "An active onboarding application already exists for provider: "
                    f"{application.provider_id}"
                )
            session.add(
                ProviderApplicationRow(
                    application_id=application.application_id,
                    provider_id=application.provider_id,
                    provider_name=application.provider_name,
                    contact_reference=application.contact_reference,
                    submitted_at=application.submitted_at,
                    status=application.status,
                )
            )

        return self._run(
            operation,
            DuplicateProviderApplicationError(
                f"Provider application already exists: {application.application_id}"
            ),
        )

    @staticmethod
    def _domain(row):
        return ProviderOnboardingApplication(
            row.application_id,
            row.provider_id,
            row.provider_name,
            row.contact_reference,
            _aware(row.submitted_at),
            row.status,
        )

    def _active(self, session, provider_id):
        return session.scalar(
            select(ProviderApplicationRow).where(
                ProviderApplicationRow.provider_id == provider_id,
                ProviderApplicationRow.status == "submitted",
            )
        )

    def get(self, application_id):
        with self._read_session() as session:
            row = session.get(ProviderApplicationRow, application_id)
            if row is None:
                raise ProviderApplicationNotFoundError(
                    f"Unknown provider application: {application_id}"
                )
            return self._domain(row)

    def list_all(self):
        with self._read_session() as session:
            rows = session.scalars(
                select(ProviderApplicationRow).order_by(
                    ProviderApplicationRow.submitted_at
                )
            ).all()
            return [self._domain(row) for row in rows]

    def list_for_provider(self, provider_id):
        return [item for item in self.list_all() if item.provider_id == provider_id]

    def active_for_provider(self, provider_id):
        with self._read_session() as session:
            row = self._active(session, provider_id)
            return self._domain(row) if row else None

    def update_status(self, application_id, status):
        def operation(session):
            row = session.get(ProviderApplicationRow, application_id)
            if row is None:
                raise ProviderApplicationNotFoundError(
                    f"Unknown provider application: {application_id}"
                )
            row.status = status
            session.flush()
            return self._domain(row)

        return self._run(
            operation, DuplicateProviderApplicationError("duplicate-application")
        )


class SqlTrustRegistryRepository(SqlRepository):
    @staticmethod
    def _domain(row):
        return ProviderTrustDecision(
            row.decision_id,
            row.provider_id,
            row.status,
            row.authority,
            row.reason,
            _aware(row.decided_at),
        )

    def add(self, decision):
        def operation(session):
            session.add(
                TrustDecisionRow(
                    decision_id=decision.decision_id,
                    provider_id=decision.provider_id,
                    status=decision.status,
                    authority=decision.authority,
                    reason=decision.reason,
                    decided_at=decision.decided_at,
                )
            )

        return self._run(
            operation,
            DuplicateTrustDecisionError(
                f"Trust decision already exists: {decision.decision_id}"
            ),
        )

    def list_all(self):
        with self._read_session() as session:
            return [
                self._domain(row)
                for row in session.scalars(
                    select(TrustDecisionRow).order_by(TrustDecisionRow.append_order)
                ).all()
            ]

    def list_for_provider(self, provider_id):
        return [item for item in self.list_all() if item.provider_id == provider_id]

    def latest_for_provider(self, provider_id):
        values = self.list_for_provider(provider_id)
        return values[-1] if values else None


class SqlTrustAttestationRepository(SqlRepository):
    def add(self, attestation):
        payload = attestation.payload
        return self._run(
            lambda session: session.add(
                TrustAttestationRow(
                    attestation_id=payload.attestation_id,
                    decision_id=payload.decision_id,
                    provider_id=payload.provider_id,
                    canonical_json=_json_model(attestation),
                    recorded_at=payload.issued_at,
                )
            ),
            DuplicateTrustAttestationError(
                f"Trust attestation already exists: {payload.attestation_id}"
            ),
        )

    @staticmethod
    def _domain(row):
        return TrustDecisionAttestation.model_validate_json(row.canonical_json)

    def get(self, attestation_id):
        with self._read_session() as session:
            row = session.get(TrustAttestationRow, attestation_id)
            if row is None:
                raise TrustAttestationNotFoundError(
                    f"Unknown trust attestation: {attestation_id}"
                )
            return self._domain(row)

    def get_by_decision(self, decision_id):
        with self._read_session() as session:
            row = session.scalar(
                select(TrustAttestationRow).where(
                    TrustAttestationRow.decision_id == decision_id
                )
            )
            return self._domain(row) if row else None

    def list_all(self):
        with self._read_session() as session:
            return [
                self._domain(row)
                for row in session.scalars(
                    select(TrustAttestationRow).order_by(
                        TrustAttestationRow.recorded_at
                    )
                ).all()
            ]

    def list_for_provider(self, provider_id):
        return [
            item for item in self.list_all() if item.payload.provider_id == provider_id
        ]


class SqlFederationBundleRepository(SqlRepository):
    def add_verified(self, bundle):
        payload = bundle.payload
        latest = self.latest_for_authority(payload.registry_authority_id)
        if latest and payload.sequence_number <= latest.payload.sequence_number:
            raise FederationBundleRepositoryError("rollback-detected")
        return self._run(
            lambda session: session.add(
                FederationBundleRow(
                    bundle_id=payload.bundle_id,
                    authority_id=payload.registry_authority_id,
                    sequence_number=payload.sequence_number,
                    bundle_hash=calculate_bundle_digest(bundle),
                    canonical_json=_json_model(bundle),
                    recorded_at=payload.issued_at,
                    accepted_at=datetime.now(timezone.utc),
                    validation_status="accepted",
                )
            ),
            FederationBundleRepositoryError("replayed-bundle"),
        )

    @staticmethod
    def _domain(row):
        return FederationBundle.model_validate_json(row.canonical_json)

    def get(self, bundle_id):
        with self._read_session() as session:
            row = session.get(FederationBundleRow, bundle_id)
            if row is None:
                raise FederationBundleNotFoundError(
                    f"Unknown federation bundle: {bundle_id}"
                )
            return self._domain(row)

    def list_all(self):
        with self._read_session() as session:
            return [
                self._domain(row)
                for row in session.scalars(
                    select(FederationBundleRow).order_by(
                        FederationBundleRow.authority_id,
                        FederationBundleRow.sequence_number,
                    )
                ).all()
            ]

    def list_for_authority(self, authority_id):
        return [
            item
            for item in self.list_all()
            if item.payload.registry_authority_id == authority_id
        ]

    def latest_for_authority(self, authority_id):
        items = self.list_for_authority(authority_id)
        return items[-1] if items else None

    def current_non_expired_for_authority(self, authority_id, now=None):
        item = self.latest_for_authority(authority_id)
        current = now or datetime.now(timezone.utc)
        return item if item and item.payload.expires_at > current else None

    def latest_digest(self, authority_id):
        item = self.latest_for_authority(authority_id)
        return calculate_bundle_digest(item) if item else None


class SqlTransparencyLogRepository(SqlRepository):
    def __init__(self, session_factory, operator):
        super().__init__(session_factory)
        self.operator = operator
        self.invalid_runtime_object_count = 0
        self.on_tree_head_created = None
        self._entry_adapter = TypeAdapter(TransparencyLogEntry)

    def append(self, entry, persist=True):
        if not validate_entry_digest(entry):
            raise TransparencyLogRepositoryError("invalid-object-digest")
        index = self.entry_count
        self._run(
            lambda session: session.add(
                TransparencyEntryRow(
                    leaf_index=index,
                    entry_id=entry.entry_id,
                    entry_type=entry.entry_type,
                    object_id=entry.object_id,
                    source_authority_id=entry.source_authority_id,
                    object_digest=entry.object_digest,
                    canonical_json=_json_model(entry),
                    recorded_at=entry.recorded_at,
                )
            ),
            TransparencyLogRepositoryError("duplicate-transparency-entry"),
        )
        return index

    def _entry(self, row):
        return self._entry_adapter.validate_json(row.canonical_json)

    def get(self, entry_id):
        with self._read_session() as session:
            row = session.scalar(
                select(TransparencyEntryRow).where(
                    TransparencyEntryRow.entry_id == entry_id
                )
            )
            if row is None:
                raise TransparencyEntryNotFoundError(
                    f"Unknown transparency entry: {entry_id}"
                )
            return self._entry(row)

    def get_by_index(self, index):
        with self._read_session() as session:
            row = session.get(TransparencyEntryRow, index)
            if row is None:
                raise TransparencyEntryNotFoundError("Unknown transparency leaf index.")
            return self._entry(row)

    def find_object(self, entry_type, object_id):
        with self._read_session() as session:
            row = session.scalar(
                select(TransparencyEntryRow).where(
                    TransparencyEntryRow.entry_type == entry_type,
                    TransparencyEntryRow.object_id == object_id,
                )
            )
            return (row.leaf_index, self._entry(row)) if row else None

    def list_entries(self):
        with self._read_session() as session:
            rows = session.scalars(
                select(TransparencyEntryRow).order_by(TransparencyEntryRow.leaf_index)
            ).all()
            return [self._entry(row) for row in rows]

    @property
    def entry_count(self):
        with self._read_session() as session:
            return session.scalar(
                select(func.count()).select_from(TransparencyEntryRow)
            )

    def _leaf_hashes(self, size=None):
        entries = self.list_entries()
        selected = entries if size is None else entries[:size]
        if size is not None and (size < 0 or size > len(entries)):
            raise TransparencyLogRepositoryError("invalid-tree-size")
        return [hash_leaf(canonicalise_model(item)) for item in selected]

    def current_root(self):
        return calculate_merkle_root(self._leaf_hashes()).hex()

    def create_current_tree_head(self, timestamp=None, tree_head_id=None):
        head = create_signed_tree_head(
            self.operator,
            self.entry_count,
            self.current_root(),
            timestamp,
            tree_head_id,
        )
        self.store_tree_head(head)
        if self.on_tree_head_created:
            self.on_tree_head_created(head.model_copy(deep=True))
        return head.model_copy(deep=True)

    def store_tree_head(self, tree_head, persist=True):
        payload = tree_head.payload
        if payload.tree_size > self.entry_count:
            raise TransparencyLogRepositoryError("tree-size-exceeds-entry-count")
        expected = calculate_merkle_root(self._leaf_hashes(payload.tree_size)).hex()
        if payload.root_hash != expected:
            raise TransparencyLogRepositoryError("tree-head-root-mismatch")
        self._run(
            lambda session: session.add(
                SignedTreeHeadRow(
                    tree_head_id=payload.tree_head_id,
                    tree_size=payload.tree_size,
                    root_hash=payload.root_hash,
                    canonical_json=_json_model(tree_head),
                    recorded_at=payload.timestamp,
                )
            ),
            TransparencyLogRepositoryError("duplicate-tree-head-id"),
        )

    @staticmethod
    def _head(row):
        return SignedTreeHead.model_validate_json(row.canonical_json)

    def list_tree_heads(self):
        with self._read_session() as session:
            return [
                self._head(row)
                for row in session.scalars(
                    select(SignedTreeHeadRow).order_by(
                        SignedTreeHeadRow.tree_size, SignedTreeHeadRow.recorded_at
                    )
                ).all()
            ]

    def get_tree_head(self, tree_head_id):
        with self._read_session() as session:
            row = session.get(SignedTreeHeadRow, tree_head_id)
            if row is None:
                raise TransparencyTreeHeadNotFoundError(
                    f"Unknown tree head: {tree_head_id}"
                )
            return self._head(row)

    def latest_tree_head(self):
        values = self.list_tree_heads()
        return values[-1] if values else None

    def inclusion_proof(self, entry_id, tree_size=None):
        entries = self.list_entries()
        index = next(
            (i for i, item in enumerate(entries) if item.entry_id == entry_id), -1
        )
        size = len(entries) if tree_size is None else tree_size
        if index < 0:
            raise TransparencyEntryNotFoundError(
                f"Unknown transparency entry: {entry_id}"
            )
        if size <= index or size <= 0 or size > len(entries):
            raise TransparencyLogRepositoryError("invalid-tree-size")
        leaves = self._leaf_hashes(size)
        return InclusionProof(
            log_id=self.operator.log_id,
            tree_size=size,
            leaf_index=index,
            entry_id=entry_id,
            leaf_hash=leaves[index].hex(),
            root_hash=calculate_merkle_root(leaves).hex(),
            audit_path=tuple(x.hex() for x in generate_inclusion_proof(leaves, index)),
        )

    def consistency_proof(self, old_size, new_size):
        if old_size < 0 or old_size > new_size or new_size > self.entry_count:
            raise TransparencyLogRepositoryError("invalid-tree-size")
        leaves = self._leaf_hashes(new_size)
        return ConsistencyProof(
            log_id=self.operator.log_id,
            old_tree_size=old_size,
            new_tree_size=new_size,
            old_root_hash=calculate_merkle_root(leaves[:old_size]).hex(),
            new_root_hash=calculate_merkle_root(leaves).hex(),
            consistency_path=tuple(
                x.hex() for x in generate_consistency_proof(leaves, old_size)
            ),
        )


class SqlWitnessStatementRepository(SqlRepository):
    invalid_runtime_object_count = 0

    def add(self, statement, persist=True):
        payload = statement.payload
        return self._run(
            lambda session: session.add(
                WitnessStatementRow(
                    statement_id=payload.statement_id,
                    witness_id=payload.witness_id,
                    tree_head_id=payload.tree_head_id,
                    canonical_json=_json_model(statement),
                    recorded_at=payload.observed_at,
                )
            ),
            ValueError("duplicate-witness-statement"),
        )

    def list_all(self):
        with self._read_session() as session:
            return [
                WitnessStatement.model_validate_json(row.canonical_json)
                for row in session.scalars(
                    select(WitnessStatementRow).order_by(
                        WitnessStatementRow.recorded_at
                    )
                ).all()
            ]

    def get(self, statement_id):
        with self._read_session() as session:
            row = session.get(WitnessStatementRow, statement_id)
            if row is None:
                raise LookupError(f"Unknown witness statement: {statement_id}")
            return WitnessStatement.model_validate_json(row.canonical_json)

    def list_by_witness(self, value):
        return [x for x in self.list_all() if x.payload.witness_id == value]

    def list_by_log(self, value):
        return [x for x in self.list_all() if x.payload.log_id == value]

    def list_by_tree_head(self, value):
        return [x for x in self.list_all() if x.payload.tree_head_id == value]

    def list_by_log_and_tree_size(self, log_id, size):
        return [
            x
            for x in self.list_all()
            if x.payload.log_id == log_id and x.payload.tree_size == size
        ]

    def find_by_witness_and_tree_head(self, witness_id, tree_head_id):
        return next(
            (
                x
                for x in self.list_all()
                if x.payload.witness_id == witness_id
                and x.payload.tree_head_id == tree_head_id
            ),
            None,
        )


class SqlCheckpointGossipRepository(SqlRepository):
    invalid_runtime_object_count = 0

    def add(self, package, persist=True):
        return self._run(
            lambda session: session.add(
                GossipObservationRow(
                    gossip_id=package.gossip_id,
                    source="local",
                    conflicting=False,
                    canonical_json=_json_model(package),
                    recorded_at=package.exported_at,
                )
            ),
            ValueError("duplicate-gossip-id"),
        )

    def get(self, gossip_id):
        with self._read_session() as session:
            row = session.get(GossipObservationRow, gossip_id)
            if row is None:
                raise LookupError(f"Unknown gossip package: {gossip_id}")
            return CheckpointGossipPackage.model_validate_json(row.canonical_json)

    def list_all(self, limit=100):
        if limit < 1 or limit > 500:
            raise ValueError("invalid-gossip-limit")
        with self._read_session() as session:
            rows = session.scalars(
                select(GossipObservationRow)
                .order_by(GossipObservationRow.recorded_at)
                .limit(limit)
            ).all()
            return [
                CheckpointGossipPackage.model_validate_json(row.canonical_json)
                for row in rows
            ]


class SqlAttributionRepository(SqlRepository):
    @staticmethod
    def _domain(row):
        return ProviderAttributionRecord(
            row.generation_id,
            row.provider_id,
            row.account_reference,
            row.prompt_hash,
            row.model_id,
            _aware(row.created_at),
            _aware(row.retained_until),
            row.retention_status,
        )

    def add(self, record):
        return self._run(
            lambda session: session.add(AttributionRecordRow(**asdict(record))),
            AttributionRecordAlreadyExistsError(
                f"An attribution record already exists for {record.generation_id}."
            ),
        )

    def get(self, generation_id):
        with self._read_session() as session:
            row = session.get(AttributionRecordRow, generation_id)
            if row is None:
                raise AttributionRecordNotFoundError(
                    f"No attribution record exists for {generation_id}."
                )
            return self._domain(row)

    def set_retention_status(self, generation_id, retention_status):
        def operation(session):
            row = session.get(AttributionRecordRow, generation_id)
            if row is None:
                raise AttributionRecordNotFoundError(
                    f"No attribution record exists for {generation_id}."
                )
            row.retention_status = retention_status
            session.flush()
            return self._domain(row)

        return self._run(
            operation, AttributionRecordAlreadyExistsError("duplicate-record")
        )

    def delete_logically(self, generation_id):
        return self.set_retention_status(generation_id, "deleted")

    def count(self):
        with self._read_session() as session:
            return session.scalar(
                select(func.count()).select_from(AttributionRecordRow)
            )


class SqlDisclosureAuditRepository(SqlRepository):
    def append(self, record):
        return self._run(
            lambda session: session.add(
                DisclosureAuditRow(
                    disclosure_id=record.disclosure_id,
                    canonical_json=json.dumps(
                        asdict(record),
                        default=str,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    approved=record.approved,
                    disclosed_at=record.disclosed_at,
                )
            ),
            ValueError("duplicate-disclosure-audit"),
        )

    def list_all(self):
        with self._read_session() as session:
            rows = session.scalars(
                select(DisclosureAuditRow).order_by(DisclosureAuditRow.disclosed_at)
            ).all()
            values = []
            for row in rows:
                data = json.loads(row.canonical_json)
                data["disclosed_at"] = datetime.fromisoformat(data["disclosed_at"])
                values.append(DisclosureAuditRecord(**data))
            return values

    def count(self):
        with self._read_session() as session:
            return session.scalar(select(func.count()).select_from(DisclosureAuditRow))
