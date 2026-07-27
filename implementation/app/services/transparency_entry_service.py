import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from app.crypto.canonical_json import canonicalise_model
from app.schemas.federation_bundle import FederationBundle
from app.schemas.transparency_entry import (
    FederationBundleLogEntry,
    TrustAttestationLogEntry,
)
from app.schemas.trust_attestation import TrustDecisionAttestation


def calculate_object_digest(public_object) -> str:
    return hashlib.sha256(canonicalise_model(public_object)).hexdigest()


def create_trust_attestation_log_entry(
    attestation: TrustDecisionAttestation,
    recorded_at: datetime | None = None,
    entry_id: str | None = None,
) -> TrustAttestationLogEntry:
    return TrustAttestationLogEntry(
        entry_id=entry_id or f"gap-log-entry-{uuid4()}",
        object_id=attestation.payload.attestation_id,
        source_authority_id=attestation.payload.registry_authority_id,
        object_digest=calculate_object_digest(attestation),
        recorded_at=recorded_at or datetime.now(timezone.utc),
        public_object=attestation,
    )


def create_federation_bundle_log_entry(
    bundle: FederationBundle,
    recorded_at: datetime | None = None,
    entry_id: str | None = None,
) -> FederationBundleLogEntry:
    return FederationBundleLogEntry(
        entry_id=entry_id or f"gap-log-entry-{uuid4()}",
        object_id=bundle.payload.bundle_id,
        source_authority_id=bundle.payload.registry_authority_id,
        object_digest=calculate_object_digest(bundle),
        recorded_at=recorded_at or datetime.now(timezone.utc),
        public_object=bundle,
    )


def validate_entry_digest(entry) -> bool:
    return entry.object_digest == calculate_object_digest(entry.public_object)
