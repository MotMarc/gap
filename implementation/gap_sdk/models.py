from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.artifact import ArtifactDescriptor, ArtifactDigest
from app.schemas.generation_credential import (
    GenerationCredential,
    GenerationCredentialPayload,
)
from app.schemas.provider_identity import (
    ProviderIdentityDocument,
    ProviderVerificationKey,
)


GapCredential = GenerationCredential
ProviderIdentity = ProviderIdentityDocument
ProviderKey = ProviderVerificationKey


class GenerationContext(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: str | None = Field(default=None, max_length=200)
    media_type: str = Field(default="application/octet-stream", max_length=255)
    generation_mode: str | None = Field(default=None, max_length=100)
    public_policy_label: str | None = Field(default=None, max_length=100)
    public_metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict
    )

    model_config = ConfigDict(extra="forbid")


class VerificationLevel(str, Enum):
    CRYPTOGRAPHIC = "cryptographic"
    TRUSTED_PROVIDER = "trusted-provider"
    FULL = "full"


class CheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"


class VerificationCheck(BaseModel):
    code: str
    name: str
    status: CheckStatus
    summary: str
    technical_detail: str | None = None
    evidence_reference: str | None = None
    required_for_overall_validity: bool = True


class VerificationResult(BaseModel):
    valid: bool
    requested_level: VerificationLevel
    achieved_level: VerificationLevel | None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    credential_id: str | None = None
    provider_id: str | None = None
    artifact_digest: str | None = None
    checks: list[VerificationCheck]
    warnings: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    failure_code: str | None = None
    failure_message: str | None = None
    summary: str
    technical_diagnostics: dict[str, Any] = Field(default_factory=dict)
    evidence_references: list[str] = Field(default_factory=list)
    artifact_integrity_valid: bool = False
    cryptographic_valid: bool = False
    provider_trusted: bool = False
    federation_state_valid: bool = False
    transparency_verified: bool = False
    witness_quorum_met: bool = False
    checkpoint_gossip_consistent: bool = False
    federation_conflict: bool = False
    split_view_detected: bool = False
    witness_equivocation_detected: bool = False


class TrustMaterialBundle(BaseModel):
    manifest: dict[str, Any]
    state: dict[str, Any]


# Stable names for public protocol objects whose detailed validation remains
# authoritative in app.schemas.
class ExtensibleProtocolObject(BaseModel):
    model_config = ConfigDict(extra="allow")


ProviderTrustDecision = ExtensibleProtocolObject
SignedTrustAttestation = ExtensibleProtocolObject
RegistryAuthorityIdentity = ExtensibleProtocolObject
FederationBundle = ExtensibleProtocolObject
TransparencyLogIdentity = ExtensibleProtocolObject
SignedTreeHead = ExtensibleProtocolObject
InclusionProof = ExtensibleProtocolObject
ConsistencyProof = ExtensibleProtocolObject
WitnessIdentity = ExtensibleProtocolObject
WitnessStatement = ExtensibleProtocolObject
GossipObservation = ExtensibleProtocolObject

__all__ = [
    "ArtifactDescriptor",
    "ArtifactDigest",
    "GenerationContext",
    "GenerationCredential",
    "GenerationCredentialPayload",
    "GapCredential",
    "ProviderIdentity",
    "ProviderKey",
    "VerificationCheck",
    "VerificationLevel",
    "VerificationResult",
    "TrustMaterialBundle",
]
