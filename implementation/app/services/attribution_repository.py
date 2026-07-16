from app.domain.provider_attribution_record import ProviderAttributionRecord


class AttributionRecordNotFoundError(LookupError):
    """
    Raised when no attribution record exists for a Generation Identifier.
    """


class AttributionRecordAlreadyExistsError(ValueError):
    """
    Raised when a record already exists for a Generation Identifier.
    """


class AttributionRepository:
    """
    In-memory private storage for Provider Attribution Records.
    """

    def __init__(self) -> None:
        self._records: dict[str, ProviderAttributionRecord] = {}

    def add(self, record: ProviderAttributionRecord) -> None:
        if record.generation_id in self._records:
            raise AttributionRecordAlreadyExistsError(
                f"An attribution record already exists for {record.generation_id}."
            )

        self._records[record.generation_id] = record

    def get(self, generation_id: str) -> ProviderAttributionRecord:
        record = self._records.get(generation_id)

        if record is None:
            raise AttributionRecordNotFoundError(
                f"No attribution record exists for {generation_id}."
            )

        return record

    def count(self) -> int:
        return len(self._records)
