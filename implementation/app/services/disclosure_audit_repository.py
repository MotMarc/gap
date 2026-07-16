from app.domain.disclosure_audit_record import DisclosureAuditRecord


class DisclosureAuditRepository:
    """
    In-memory append-only disclosure audit log.
    """

    def __init__(self) -> None:
        self._records: list[DisclosureAuditRecord] = []

    def append(self, record: DisclosureAuditRecord) -> None:
        self._records.append(record)

    def list_all(self) -> list[DisclosureAuditRecord]:
        return list(self._records)

    def count(self) -> int:
        return len(self._records)
