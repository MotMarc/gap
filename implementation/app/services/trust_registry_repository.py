from app.domain.provider_trust import ProviderTrustDecision


class DuplicateTrustDecisionError(ValueError):
    """
    Raised when a trust decision ID is already stored.
    """


class TrustRegistryRepository:
    """
    In-memory append-only repository of provider trust decisions.
    """

    def __init__(
        self,
        decisions: list[ProviderTrustDecision] | None = None,
    ) -> None:
        self._decisions: list[ProviderTrustDecision] = []
        self._decision_ids: set[str] = set()

        for decision in decisions or []:
            self.add(decision)

    def add(self, decision: ProviderTrustDecision) -> None:
        if decision.decision_id in self._decision_ids:
            raise DuplicateTrustDecisionError(
                f"Trust decision already exists: {decision.decision_id}"
            )

        self._decisions.append(decision)
        self._decision_ids.add(decision.decision_id)

    def list_all(self) -> list[ProviderTrustDecision]:
        return list(self._decisions)

    def list_for_provider(
        self,
        provider_id: str,
    ) -> list[ProviderTrustDecision]:
        return [
            decision
            for decision in self._decisions
            if decision.provider_id == provider_id
        ]

    def latest_for_provider(
        self,
        provider_id: str,
    ) -> ProviderTrustDecision | None:
        decisions = self.list_for_provider(provider_id)

        if not decisions:
            return None

        return decisions[-1]
