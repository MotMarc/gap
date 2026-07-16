from dataclasses import replace

from app.domain.provider_attribution_record import (
    ProviderAttributionRecord,
    RetentionStatus,
)


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

    This repository is intentionally isolated from the public credential
    repository and verification workflow.
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

    def set_retention_status(
        self,
        generation_id: str,
        retention_status: RetentionStatus,
    ) -> ProviderAttributionRecord:
        """
        Replace a record with an immutable copy containing a new status.
        """

        current_record = self.get(generation_id)

        updated_record = replace(
            current_record,
            retention_status=retention_status,
        )

        self._records[generation_id] = updated_record

        return updated_record

    def delete_logically(
        self,
        generation_id: str,
    ) -> ProviderAttributionRecord:
        """
        Mark a record as deleted without removing its lifecycle metadata.

        A production implementation may separately purge protected fields
        according to provider policy and applicable law.
        """

        return self.set_retention_status(
            generation_id=generation_id,
            retention_status="deleted",
        )

    def count(self) -> int:
        return len(self._records)
