from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SchemaRevision(Base):
    __tablename__ = "schema_revision"
    revision: Mapped[str] = mapped_column(String(64), primary_key=True)
    applied_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)


class ProviderApplicationRow(Base):
    __tablename__ = "provider_applications"
    application_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    provider_id: Mapped[str] = mapped_column(String(200), index=True)
    provider_name: Mapped[str] = mapped_column(String(500))
    contact_reference: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))
    __table_args__ = (
        CheckConstraint(
            "status IN ('submitted','approved','rejected','withdrawn')",
            name="ck_application_status",
        ),
    )


class TrustDecisionRow(Base):
    __tablename__ = "trust_decisions"
    append_order: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    decision_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    provider_id: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(32))
    authority: Mapped[str] = mapped_column(String(500))
    reason: Mapped[str] = mapped_column(Text)
    decided_at: Mapped[object] = mapped_column(DateTime(timezone=True))


class SignedObjectMixin:
    canonical_json: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)


class TrustAttestationRow(SignedObjectMixin, Base):
    __tablename__ = "trust_attestations"
    attestation_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    decision_id: Mapped[str] = mapped_column(String(200), unique=True)
    provider_id: Mapped[str] = mapped_column(String(200), index=True)


class FederationBundleRow(SignedObjectMixin, Base):
    __tablename__ = "federation_bundles"
    bundle_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    authority_id: Mapped[str] = mapped_column(String(200), index=True)
    sequence_number: Mapped[int] = mapped_column(Integer)
    bundle_hash: Mapped[str] = mapped_column(String(64))
    accepted_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    import_provenance: Mapped[str | None] = mapped_column(String(500))
    validation_status: Mapped[str] = mapped_column(String(32), default="accepted")
    __table_args__ = (
        UniqueConstraint(
            "authority_id", "sequence_number", name="uq_bundle_authority_seq"
        ),
    )


class TransparencyEntryRow(SignedObjectMixin, Base):
    __tablename__ = "transparency_entries"
    leaf_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[str] = mapped_column(String(200), unique=True)
    entry_type: Mapped[str] = mapped_column(String(80))
    object_id: Mapped[str] = mapped_column(String(200))
    source_authority_id: Mapped[str] = mapped_column(String(200))
    object_digest: Mapped[str] = mapped_column(String(64))
    __table_args__ = (
        UniqueConstraint("entry_type", "object_id", name="uq_transparency_object"),
    )


class SignedTreeHeadRow(SignedObjectMixin, Base):
    __tablename__ = "signed_tree_heads"
    tree_head_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    tree_size: Mapped[int] = mapped_column(Integer, index=True)
    root_hash: Mapped[str] = mapped_column(String(64))


class WitnessStatementRow(SignedObjectMixin, Base):
    __tablename__ = "witness_statements"
    statement_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    witness_id: Mapped[str] = mapped_column(String(200))
    tree_head_id: Mapped[str] = mapped_column(String(200))
    __table_args__ = (
        UniqueConstraint("witness_id", "tree_head_id", name="uq_witness_tree_head"),
    )


class GossipObservationRow(SignedObjectMixin, Base):
    __tablename__ = "gossip_observations"
    gossip_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    source: Mapped[str] = mapped_column(String(200), default="local")
    conflicting: Mapped[bool] = mapped_column(Boolean, default=False)


class AttributionRecordRow(Base):
    __tablename__ = "attribution_records"
    generation_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    provider_id: Mapped[str] = mapped_column(String(200), index=True)
    account_reference: Mapped[str] = mapped_column(Text)
    prompt_hash: Mapped[str] = mapped_column(String(64))
    model_id: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    retained_until: Mapped[object] = mapped_column(DateTime(timezone=True))
    retention_status: Mapped[str] = mapped_column(String(32))


class DisclosureAuditRow(Base):
    __tablename__ = "disclosure_audits"
    disclosure_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    canonical_json: Mapped[str] = mapped_column(Text)
    approved: Mapped[bool] = mapped_column(Boolean)
    disclosed_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)


class AdministrativeAuditRow(Base):
    __tablename__ = "administrative_audits"
    event_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    action: Mapped[str] = mapped_column(String(100))
    target_id: Mapped[str] = mapped_column(String(200))
    request_id: Mapped[str] = mapped_column(String(200))
    outcome: Mapped[str] = mapped_column(String(32))
    actor_fingerprint: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    details_json: Mapped[str] = mapped_column(Text)


class BackupRecordRow(Base):
    __tablename__ = "backup_records"
    backup_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    manifest_json: Mapped[str] = mapped_column(Text)
    signature: Mapped[bytes | None] = mapped_column(LargeBinary)
