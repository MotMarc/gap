from __future__ import annotations

from typing import Any

import httpx

from .errors import NetworkError, ServiceError
from .version import __version__


class GapServiceClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        verify_tls: bool = True,
        transport: httpx.BaseTransport | None = None,
        max_response_bytes: int = 5 * 1024 * 1024,
    ):
        self.base_url = base_url.rstrip("/")
        self.max_response_bytes = max_response_bytes
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            verify=verify_tls,
            transport=transport,
            headers={"User-Agent": f"gap-python-sdk/{__version__}"},
        )

    def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise NetworkError("The GAP service is unavailable.") from exc
        if len(response.content) > self.max_response_bytes:
            raise ServiceError("The GAP service response exceeded the size limit.")
        if response.is_error:
            raise ServiceError(f"The GAP service returned HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError as exc:
            raise ServiceError("The GAP service returned malformed JSON.") from exc

    def health(self) -> dict:
        return self._request("GET", "/health")

    def get_provider(self, provider_id: str) -> dict:
        return self._request("GET", f"/providers/{provider_id}/.well-known/gap.json")

    def verify_credential(self, credential) -> dict:
        data = (
            credential.model_dump(mode="json")
            if hasattr(credential, "model_dump")
            else credential
        )
        return self._request("POST", "/credentials/verify", json={"credential": data})

    def export_trust_material(self, output=None, *, overwrite: bool = False):
        from .trust import save_trust_material

        state = self._request("GET", "/public-state")
        required = {
            "providers",
            "registry_authorities",
            "trust_decisions",
            "trust_attestations",
            "transparency_log_identities",
            "transparency_entries",
            "signed_tree_heads",
            "inclusion_proofs",
            "witness_identities",
            "witness_statements",
            "witness_quorum_policy",
            "gossip_observations",
        }
        if (
            required - set(state)
            or state.get("supported_maximum_verification_level") != "full"
            or state.get("private_data_included") is not False
        ):
            raise ServiceError(
                "The GAP service returned incomplete public trust material."
            )
        if output is None:
            return state
        return save_trust_material(state, output, overwrite=overwrite)

    def __repr__(self) -> str:
        return f"GapServiceClient(base_url={self.base_url!r})"


class GapAdministrativeClient(GapServiceClient):
    def __init__(self, base_url: str, token: str, **kwargs):
        if not (
            base_url.startswith("https://")
            or base_url.startswith("http://127.0.0.1")
            or base_url.startswith("http://localhost")
        ):
            raise ValueError(
                "Administrative clients require HTTPS outside local development."
            )
        super().__init__(base_url, **kwargs)
        self._client.headers["Authorization"] = f"Bearer {token}"

    def transition_provider_trust(
        self, provider_id: str, *, status: str, reason: str, authority=None
    ) -> dict:
        body = {"status": status, "reason": reason}
        if authority:
            body["authority"] = authority
        return self._request("POST", f"/admin/providers/{provider_id}/trust", json=body)

    def audit_events(self) -> dict:
        return self._request("GET", "/admin/audit")

    def __repr__(self) -> str:
        return f"GapAdministrativeClient(base_url={self.base_url!r}, token=<redacted>)"
