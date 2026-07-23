from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.provider_trust import ProviderTrustStatus
from app.services.federation_bundle_service import verify_federation_bundle
from app.services.trust_attestation_service import verify_trust_attestation_details


@dataclass(frozen=True, slots=True)
class FederationTrustSource:
    registry_authority_id: str
    provider_status: ProviderTrustStatus
    decision_id: str
    attestation_id: str
    bundle_id: str | None
    bundle_sequence: int | None
    bundle_issued_at: datetime | None
    bundle_expires_at: datetime | None
    authority_key_id: str
    authority_key_status: str | None
    attestation_valid: bool
    bundle_valid: bool
    source_type: str


@dataclass(frozen=True, slots=True)
class FederatedTrustEvaluation:
    provider_id: str
    effective_status: ProviderTrustStatus | None
    trusted: bool
    federation_conflict: bool
    authority_sources: tuple[FederationTrustSource, ...]
    supporting_authority_ids: tuple[str, ...]
    conflicting_authority_ids: tuple[str, ...]
    bundle_ids: tuple[str, ...]
    failure_reason: str | None

    @property
    def source_count(self) -> int:
        return len(self.authority_sources)


class FederatedTrustService:
    def __init__(
        self,
        local_trust_service,
        authority_repository,
        bundle_repository,
        local_authority_id: str,
    ) -> None:
        self.local_trust_service = local_trust_service
        self.authority_repository = authority_repository
        self.bundle_repository = bundle_repository
        self.local_authority_id = local_authority_id

    def evaluate(self, provider_id: str, now: datetime | None = None):
        current_time = now or datetime.now(timezone.utc)
        sources: list[FederationTrustSource] = []
        local = self.local_trust_service.evaluate_provider_trust(provider_id)
        attestation = self.local_trust_service.get_current_attestation(provider_id)
        if local.attestation_valid and attestation is not None:
            sources.append(
                FederationTrustSource(
                    registry_authority_id=attestation.payload.registry_authority_id,
                    provider_status=attestation.payload.status,
                    decision_id=attestation.payload.decision_id,
                    attestation_id=attestation.payload.attestation_id,
                    bundle_id=None,
                    bundle_sequence=None,
                    bundle_issued_at=None,
                    bundle_expires_at=None,
                    authority_key_id=attestation.proof.key_id,
                    authority_key_status=local.authority_key_status,
                    attestation_valid=True,
                    bundle_valid=True,
                    source_type="local",
                )
            )
        for authority in self.authority_repository.list_all():
            if authority.authority_id == self.local_authority_id:
                continue
            bundle = self.bundle_repository.current_non_expired_for_authority(
                authority.authority_id, current_time
            )
            if bundle is None:
                continue
            # Accepted history is revalidated for current freshness/key lifecycle.
            verification = verify_federation_bundle(
                bundle, self.authority_repository, None, current_time
            )
            if not verification.valid:
                continue
            match = next(
                (
                    item
                    for item in bundle.payload.attestations
                    if item.payload.provider_id == provider_id
                ),
                None,
            )
            if match is None:
                continue
            attestation_verification = verify_trust_attestation_details(
                match, self.authority_repository
            )
            if not attestation_verification.valid:
                continue
            sources.append(
                FederationTrustSource(
                    registry_authority_id=authority.authority_id,
                    provider_status=match.payload.status,
                    decision_id=match.payload.decision_id,
                    attestation_id=match.payload.attestation_id,
                    bundle_id=bundle.payload.bundle_id,
                    bundle_sequence=bundle.payload.sequence_number,
                    bundle_issued_at=bundle.payload.issued_at,
                    bundle_expires_at=bundle.payload.expires_at,
                    authority_key_id=match.proof.key_id,
                    authority_key_status=attestation_verification.key_status,
                    attestation_valid=True,
                    bundle_valid=True,
                    source_type="federated-bundle",
                )
            )
        if not sources:
            return FederatedTrustEvaluation(
                provider_id, None, False, False, (), (), (), (), "no-valid-trust-source"
            )
        statuses = {source.provider_status for source in sources}
        authority_ids = tuple(source.registry_authority_id for source in sources)
        bundle_ids = tuple(
            source.bundle_id for source in sources if source.bundle_id is not None
        )
        if len(statuses) > 1:
            return FederatedTrustEvaluation(
                provider_id,
                None,
                False,
                True,
                tuple(sources),
                (),
                authority_ids,
                bundle_ids,
                "federation-conflict",
            )
        effective = next(iter(statuses))
        trusted = effective == "approved"
        return FederatedTrustEvaluation(
            provider_id,
            effective,
            trusted,
            False,
            tuple(sources),
            authority_ids if trusted else (),
            (),
            bundle_ids,
            None if trusted else "provider-not-approved",
        )
