from app.schemas.trust_attestation import TrustDecisionAttestation


class DuplicateTrustAttestationError(ValueError):
    pass


class TrustAttestationNotFoundError(LookupError):
    pass


class TrustAttestationRepository:
    def __init__(
        self, attestations: list[TrustDecisionAttestation] | None = None
    ) -> None:
        self._attestations: list[TrustDecisionAttestation] = []
        self._ids: set[str] = set()
        self._decision_ids: set[str] = set()
        for attestation in attestations or []:
            self.add(attestation)

    def add(self, attestation: TrustDecisionAttestation) -> None:
        if attestation.payload.attestation_id in self._ids:
            raise DuplicateTrustAttestationError(
                f"Trust attestation already exists: {attestation.payload.attestation_id}"
            )
        if attestation.payload.decision_id in self._decision_ids:
            raise DuplicateTrustAttestationError(
                "A trust attestation already binds decision: "
                f"{attestation.payload.decision_id}"
            )
        self._attestations.append(attestation)
        self._ids.add(attestation.payload.attestation_id)
        self._decision_ids.add(attestation.payload.decision_id)

    def get(self, attestation_id: str) -> TrustDecisionAttestation:
        result = next(
            (
                item
                for item in self._attestations
                if item.payload.attestation_id == attestation_id
            ),
            None,
        )
        if result is None:
            raise TrustAttestationNotFoundError(
                f"Unknown trust attestation: {attestation_id}"
            )
        return result

    def get_by_decision(self, decision_id: str) -> TrustDecisionAttestation | None:
        return next(
            (
                item
                for item in self._attestations
                if item.payload.decision_id == decision_id
            ),
            None,
        )

    def list_all(self) -> list[TrustDecisionAttestation]:
        return list(self._attestations)

    def list_for_provider(self, provider_id: str) -> list[TrustDecisionAttestation]:
        return [
            item
            for item in self._attestations
            if item.payload.provider_id == provider_id
        ]
