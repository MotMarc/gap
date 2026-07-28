import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "implementation"))

from app.core.settings import Settings, hash_admin_token  # noqa: E402
from app.database.engine import Database, create_database_engine  # noqa: E402
from app.database.migrations import (  # noqa: E402
    HEAD_REVISION,
    current_revision,
    require_head,
    upgrade_to_head,
)
from app.database.models import TrustDecisionRow  # noqa: E402
from app.database.repositories import (  # noqa: E402
    SqlProviderApplicationRepository,
    SqlTrustRegistryRepository,
)
from app.database.uow import UnitOfWork  # noqa: E402
from app.domain.provider_application import ProviderOnboardingApplication  # noqa: E402
from app.domain.provider_trust import ProviderTrustDecision  # noqa: E402
from app.main import app  # noqa: E402


def sqlite_database(tmp_path):
    database = Database(f"sqlite:///{(tmp_path / 'state.db').as_posix()}")
    upgrade_to_head(database.engine)
    return database


def test_settings_load_from_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("APP_ENV", "demonstration")
    monkeypatch.setenv("PERSISTENCE_MODE", "database")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'gap.db').as_posix()}")
    settings = Settings()
    assert settings.app_env == "demonstration"
    assert settings.persistence_mode == "database"


def test_invalid_persistence_mode_fails() -> None:
    with pytest.raises(ValueError):
        Settings(persistence_mode="files")


def test_production_rejects_memory_and_wildcard_cors() -> None:
    with pytest.raises(ValueError, match="database persistence"):
        Settings(app_env="production", persistence_mode="memory")
    with pytest.raises(ValueError, match="Wildcard CORS"):
        Settings(
            app_env="production",
            persistence_mode="database",
            cors_allowed_origins=["*"],
        )


def test_admin_requires_a_hashed_secret() -> None:
    with pytest.raises(ValueError, match="ADMIN_API_TOKEN_HASH"):
        Settings(admin_api_enabled=True)
    assert len(hash_admin_token("high-entropy-test-token")) == 64


def test_migration_reaches_head(tmp_path) -> None:
    engine = create_database_engine(
        f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    )
    assert current_revision(engine) is None
    assert upgrade_to_head(engine) == HEAD_REVISION
    require_head(engine)
    assert current_revision(engine) == HEAD_REVISION
    engine.dispose()


def test_application_persists_across_sessions(tmp_path) -> None:
    database = sqlite_database(tmp_path)
    repository = SqlProviderApplicationRepository(database.session_factory)
    application = ProviderOnboardingApplication(
        "application-14",
        "persistent-provider",
        "Persistent Provider",
        "private-contact",
        datetime.now(timezone.utc),
    )
    repository.add(application)
    reloaded = SqlProviderApplicationRepository(database.session_factory)
    assert reloaded.get(application.application_id) == application
    database.dispose()


def test_trust_decisions_preserve_append_order_and_duplicates_are_domain_errors(
    tmp_path,
) -> None:
    database = sqlite_database(tmp_path)
    repository = SqlTrustRegistryRepository(database.session_factory)
    first = ProviderTrustDecision(
        "decision-1",
        "provider",
        "applicant",
        "authority",
        "review",
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    second = ProviderTrustDecision(
        "decision-2",
        "provider",
        "approved",
        "authority",
        "approved",
        datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    repository.add(first)
    repository.add(second)
    assert repository.list_all() == [first, second]
    with pytest.raises(ValueError, match="already exists"):
        repository.add(first)
    database.dispose()


def test_failed_unit_of_work_rolls_back_every_write(tmp_path) -> None:
    database = sqlite_database(tmp_path)
    with pytest.raises(RuntimeError):
        with UnitOfWork(database.session_factory) as uow:
            uow.session.add(
                TrustDecisionRow(
                    decision_id="rolled-back",
                    provider_id="provider",
                    status="applicant",
                    authority="authority",
                    reason="test",
                    decided_at=datetime.now(timezone.utc),
                )
            )
            raise RuntimeError("fail")
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(TrustDecisionRow)) == 0
    database.dispose()


def test_database_constraint_rejects_duplicate_decision(tmp_path) -> None:
    database = sqlite_database(tmp_path)
    now = datetime.now(timezone.utc)
    with pytest.raises(IntegrityError):
        with database.session() as session:
            for _ in range(2):
                session.add(
                    TrustDecisionRow(
                        decision_id="same",
                        provider_id="provider",
                        status="applicant",
                        authority="authority",
                        reason="test",
                        decided_at=now,
                    )
                )
    database.dispose()


def test_request_ids_and_safe_errors() -> None:
    client = TestClient(app)
    supplied = "buyer-demo-request-14"
    response = client.get(
        "/providers/does-not-exist/.well-known/gap.json",
        headers={"X-Request-ID": supplied},
    )
    assert response.headers["X-Request-ID"] == supplied
    assert response.json()["error"]["request_id"] == supplied
    invalid = client.get(
        "/providers/does-not-exist/.well-known/gap.json",
        headers={"X-Request-ID": "bad value"},
    )
    assert invalid.headers["X-Request-ID"] != "bad value"


def test_liveness_and_readiness_are_distinct() -> None:
    client = TestClient(app)
    assert client.get("/health/live").json()["status"] == "alive"
    app.state.ready = False
    assert client.get("/health/ready").status_code == 503
    app.state.ready = True


def test_admin_endpoint_rejects_missing_and_invalid_token() -> None:
    settings = app.state.settings
    original_enabled = settings.admin_api_enabled
    original_hash = settings.admin_api_token_hash
    settings.admin_api_enabled = True
    settings.admin_api_token_hash = hashlib.sha256(b"correct").hexdigest()
    try:
        client = TestClient(app)
        url = "/admin/providers/gap-demo-provider/trust"
        body = {"status": "suspended", "reason": "test"}
        assert client.post(url, json=body).status_code == 401
        assert (
            client.post(
                url, json=body, headers={"Authorization": "Bearer wrong"}
            ).status_code
            == 403
        )
    finally:
        settings.admin_api_enabled = original_enabled
        settings.admin_api_token_hash = original_hash
