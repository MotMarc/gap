from __future__ import annotations

from contextlib import AbstractContextManager
from contextvars import ContextVar


CURRENT_SESSION: ContextVar[object | None] = ContextVar(
    "gap_current_database_session", default=None
)


class UnitOfWork(AbstractContextManager):
    """Explicit transaction boundary for coordinated repository operations."""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.session = None

    def __enter__(self):
        self.session = self.session_factory()
        self.transaction = self.session.begin()
        self.transaction.__enter__()
        self._token = CURRENT_SESSION.set(self.session)
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            return self.transaction.__exit__(exc_type, exc, traceback)
        finally:
            CURRENT_SESSION.reset(self._token)
            self.session.close()
