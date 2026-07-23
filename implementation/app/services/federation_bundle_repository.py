from datetime import datetime, timezone

from app.schemas.federation_bundle import FederationBundle
from app.services.federation_bundle_service import calculate_bundle_digest


class FederationBundleRepositoryError(ValueError):
    pass


class FederationBundleNotFoundError(LookupError):
    pass


class FederationBundleRepository:
    def __init__(self) -> None:
        self._bundles: dict[str, FederationBundle] = {}

    def add_verified(self, bundle: FederationBundle) -> None:
        payload = bundle.payload
        if payload.bundle_id in self._bundles:
            raise FederationBundleRepositoryError("replayed-bundle")
        history = self.list_for_authority(payload.registry_authority_id)
        if any(
            item.payload.sequence_number == payload.sequence_number for item in history
        ):
            raise FederationBundleRepositoryError("replayed-bundle")
        if history and payload.sequence_number <= history[-1].payload.sequence_number:
            raise FederationBundleRepositoryError("rollback-detected")
        self._bundles[payload.bundle_id] = bundle.model_copy(deep=True)

    def get(self, bundle_id: str) -> FederationBundle:
        try:
            return self._bundles[bundle_id].model_copy(deep=True)
        except KeyError as error:
            raise FederationBundleNotFoundError(
                f"Unknown federation bundle: {bundle_id}"
            ) from error

    def list_all(self) -> list[FederationBundle]:
        return [item.model_copy(deep=True) for item in self._bundles.values()]

    def list_for_authority(self, authority_id: str) -> list[FederationBundle]:
        return sorted(
            [
                item.model_copy(deep=True)
                for item in self._bundles.values()
                if item.payload.registry_authority_id == authority_id
            ],
            key=lambda item: item.payload.sequence_number,
        )

    def latest_for_authority(self, authority_id: str) -> FederationBundle | None:
        items = self.list_for_authority(authority_id)
        return items[-1] if items else None

    def current_non_expired_for_authority(
        self, authority_id: str, now: datetime | None = None
    ) -> FederationBundle | None:
        latest = self.latest_for_authority(authority_id)
        current_time = now or datetime.now(timezone.utc)
        return latest if latest and latest.payload.expires_at > current_time else None

    def latest_digest(self, authority_id: str) -> str | None:
        latest = self.latest_for_authority(authority_id)
        return calculate_bundle_digest(latest) if latest else None
