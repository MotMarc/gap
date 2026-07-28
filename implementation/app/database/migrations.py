from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import inspect, select

from app.database.models import Base, SchemaRevision


HEAD_REVISION = "001_sprint14_initial"


class MigrationStateError(RuntimeError):
    pass


def upgrade_to_head(engine) -> str:
    """Apply deterministic, explicitly invoked schema migrations."""
    # The ordered table list is the immutable body of revision 001. Application
    # startup never calls this function and never invokes metadata.create_all.
    with engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            table.create(connection, checkfirst=True)
    with engine.begin() as connection:
        existing = connection.execute(select(SchemaRevision.revision)).scalars().all()
        if existing and existing != [HEAD_REVISION]:
            raise MigrationStateError(f"Unsupported migration history: {existing!r}")
        if not existing:
            connection.execute(
                SchemaRevision.__table__.insert().values(
                    revision=HEAD_REVISION, applied_at=datetime.now(timezone.utc)
                )
            )
    return HEAD_REVISION


def current_revision(engine) -> str | None:
    if "schema_revision" not in inspect(engine).get_table_names():
        return None
    with engine.connect() as connection:
        return connection.execute(select(SchemaRevision.revision)).scalar_one_or_none()


def require_head(engine) -> None:
    revision = current_revision(engine)
    if revision != HEAD_REVISION:
        raise MigrationStateError(
            f"Database migration is {revision or 'uninitialised'}; expected {HEAD_REVISION}."
        )
