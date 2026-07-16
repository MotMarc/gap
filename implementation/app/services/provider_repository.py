from app.domain.provider import Provider


class ProviderNotFoundError(LookupError):
    """
    Raised when a requested provider does not exist.
    """


class ProviderRepository:
    """
    In-memory repository of participating GAP providers.

    A persistent repository can replace this implementation later without
    changing the protocol services that depend on it.
    """

    def __init__(self, providers: list[Provider] | None = None) -> None:
        self._providers: dict[str, Provider] = {}

        for provider in providers or []:
            self.add(provider)

    def add(self, provider: Provider) -> None:
        if provider.provider_id in self._providers:
            raise ValueError(f"Provider already exists: {provider.provider_id}")

        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> Provider:
        provider = self._providers.get(provider_id)

        if provider is None:
            raise ProviderNotFoundError(f"Unknown provider: {provider_id}")

        return provider

    def list_all(self) -> list[Provider]:
        return list(self._providers.values())
