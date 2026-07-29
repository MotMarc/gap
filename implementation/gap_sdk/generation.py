from __future__ import annotations

import base64
import ipaddress
from typing import Protocol
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .errors import ProviderAdapterError


class GenerationCapabilities(BaseModel):
    provider_name: str
    media_types: list[str]
    maximum_prompt_length: int = Field(gt=0, le=100_000)
    maximum_response_bytes: int = Field(gt=0)
    deterministic: bool = False
    model_config = ConfigDict(extra="forbid")


class GenerationRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=100_000)
    request_id: str | None = Field(default=None, max_length=200)
    media_type: str = Field(default="image/png", max_length=255)
    model_config = ConfigDict(extra="forbid")


class GenerationResult(BaseModel):
    artifact: bytes
    media_type: str
    filename: str
    model_id: str
    request_id: str | None = None
    model_config = ConfigDict(extra="forbid")


class GenerationProviderAdapter(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def capabilities(self) -> GenerationCapabilities: ...

    def generate(self, request: GenerationRequest) -> GenerationResult: ...


class HttpGenerationProviderAdapter:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 30,
        verify_tls: bool = True,
        authorization: str | None = None,
        maximum_response_bytes: int = 10 * 1024 * 1024,
        allow_private_network: bool = False,
        transport: httpx.BaseTransport | None = None,
    ):
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ProviderAdapterError("Provider URL is invalid.")
        if parsed.scheme != "https" and parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ProviderAdapterError(
                "External providers require HTTPS outside local development."
            )
        try:
            address = ipaddress.ip_address(parsed.hostname)
            if (
                not allow_private_network
                and not address.is_loopback
                and (
                    address.is_private or address.is_link_local or address.is_multicast
                )
            ):
                raise ProviderAdapterError("Provider URL targets a restricted network.")
        except ValueError:
            pass
        self.base_url = base_url.rstrip("/")
        self.maximum_response_bytes = maximum_response_bytes
        headers = {"User-Agent": "gap-generation-adapter/0.16"}
        if authorization:
            headers["Authorization"] = authorization
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            verify=verify_tls,
            follow_redirects=False,
            headers=headers,
            transport=transport,
        )
        self._capabilities = None

    @property
    def provider_name(self) -> str:
        return self.capabilities.provider_name

    @property
    def capabilities(self) -> GenerationCapabilities:
        if self._capabilities is None:
            self._capabilities = GenerationCapabilities.model_validate(
                self._request("GET", "/.well-known/generation-provider.json")
            )
        return self._capabilities

    def _request(self, method, path, **kwargs):
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise ProviderAdapterError("Generation provider is unavailable.") from exc
        if response.is_redirect:
            raise ProviderAdapterError("Generation provider redirects are refused.")
        if len(response.content) > self.maximum_response_bytes:
            raise ProviderAdapterError(
                "Generation provider response exceeded the size limit."
            )
        if response.is_error:
            raise ProviderAdapterError(
                f"Generation provider returned HTTP {response.status_code}."
            )
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderAdapterError(
                "Generation provider returned malformed JSON."
            ) from exc

    def generate(self, request: GenerationRequest | dict) -> GenerationResult:
        request = GenerationRequest.model_validate(request)
        capabilities = self.capabilities
        if request.media_type not in capabilities.media_types:
            raise ProviderAdapterError(
                "Generation provider does not support the media type."
            )
        if len(request.prompt) > capabilities.maximum_prompt_length:
            raise ProviderAdapterError("Prompt exceeds the provider limit.")
        data = self._request("POST", "/generate", json=request.model_dump())
        try:
            artifact = base64.b64decode(data.pop("artifact_base64"), validate=True)
            result = GenerationResult(artifact=artifact, **data)
        except (KeyError, ValueError, TypeError) as exc:
            raise ProviderAdapterError(
                "Generation provider response is malformed."
            ) from exc
        if len(result.artifact) > min(
            capabilities.maximum_response_bytes, self.maximum_response_bytes
        ):
            raise ProviderAdapterError("Generated artifact exceeded the size limit.")
        if result.media_type not in capabilities.media_types:
            raise ProviderAdapterError(
                "Generation provider returned an unsupported media type."
            )
        return result

    def __repr__(self):
        return f"HttpGenerationProviderAdapter(base_url={self.base_url!r}, authorization=<redacted>)"
