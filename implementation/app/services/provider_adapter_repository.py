from app.services.provider_adapter import ProviderGenerationAdapter


class ProviderAdapterNotFoundError(LookupError):
    """
    Raised when no generation adapter is registered for a provider.
    """


class ProviderAdapterRepository:
    """
    In-memory repository for provider generation adapters.
    """

    def __init__(
        self,
        adapters: list[ProviderGenerationAdapter] | None = None,
    ) -> None:
        self._adapters: dict[str, ProviderGenerationAdapter] = {}

        for adapter in adapters or []:
            self.add(adapter)

    def add(
        self,
        adapter: ProviderGenerationAdapter,
    ) -> None:
        provider_id = adapter.provider_id

        if provider_id in self._adapters:
            raise ValueError(f"An adapter already exists for provider: {provider_id}")

        self._adapters[provider_id] = adapter

    def get(
        self,
        provider_id: str,
    ) -> ProviderGenerationAdapter:
        adapter = self._adapters.get(provider_id)

        if adapter is None:
            raise ProviderAdapterNotFoundError(
                f"No generation adapter exists for provider: {provider_id}"
            )

        return adapter

    def list_provider_ids(self) -> list[str]:
        return list(self._adapters.keys())
