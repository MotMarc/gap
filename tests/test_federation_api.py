import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


IMPLEMENTATION_DIRECTORY = Path(__file__).resolve().parents[1] / "implementation"
sys.path.insert(0, str(IMPLEMENTATION_DIRECTORY))

from app.core.registry_authority_config import REFERENCE_REGISTRY_AUTHORITY  # noqa: E402
from app.core.repositories import (  # noqa: E402
    federation_bundle_repository,
    trust_attestation_repository,
)
from app.main import app  # noqa: E402
from app.services.federation_bundle_service import issue_federation_bundle  # noqa: E402


client = TestClient(app)


def make_bundle(bundle_id: str):
    now = datetime.now(timezone.utc)
    latest = {}
    for item in trust_attestation_repository.list_all():
        latest[item.payload.provider_id] = item
    return issue_federation_bundle(
        REFERENCE_REGISTRY_AUTHORITY,
        latest.values(),
        1,
        now,
        now + timedelta(days=1),
        bundle_id=bundle_id,
    )


def test_federation_endpoints_and_stateless_verification() -> None:
    before = len(federation_bundle_repository.list_all())
    bundle = make_bundle("api-stateless-bundle")
    verification = client.post(
        "/federation/bundles/verify",
        json=bundle.model_dump(mode="json"),
    )
    assert verification.status_code == 200
    assert verification.json()["valid"] is True
    assert len(federation_bundle_repository.list_all()) == before
    assert client.get("/federation/bundles").status_code == 200
    assert client.get("/federation/bundles/unknown").status_code == 404
    assert client.get("/federation/authorities/unknown/chain").status_code == 404


def test_tampered_bundle_is_rejected_without_persistence() -> None:
    before = len(federation_bundle_repository.list_all())
    bundle = make_bundle("api-tamper-bundle")
    data = bundle.model_dump(mode="json")
    data["payload"]["bundle_id"] = "changed"
    response = client.post("/federation/bundles/verify", json=data)
    assert response.status_code == 200
    assert response.json()["failure_reason"] == "invalid-bundle-signature"
    assert len(federation_bundle_repository.list_all()) == before


def test_trust_responses_expose_federation_provenance() -> None:
    provider = client.get("/providers/gap-demo-provider/trust").json()
    assert provider["effective_status"] == "approved"
    assert provider["federation_conflict"] is False
    assert provider["federation_source_count"] == 1
    assert provider["federation_sources"][0]["source_type"] == "local"
    registry = client.get("/trust-registry").json()
    assert all("federation_conflict" in entry for entry in registry)
