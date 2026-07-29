from __future__ import annotations

import base64
import hashlib
from datetime import timezone
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.crypto.canonical_json import canonicalise_model
from app.crypto.provider_keys import encode_public_key, load_private_key
from app.schemas.artifact import ArtifactDescriptor, ArtifactDigest
from app.schemas.generation_credential import (
    CredentialGeneration,
    CredentialModel,
    CredentialProvider,
    GenerationCredential,
    GenerationCredentialPayload,
    GenerationCredentialProof,
)
from app.services.verification_service import verify_generation_credential

from .errors import CredentialError, KeyError
from .files import read_sidecar, sha256_file, write_sidecar
from .models import GenerationContext, ProviderIdentity
from .interop import RAW_BINDING


class CredentialSigner(Protocol):
    @property
    def key_id(self) -> str: ...

    def sign(self, payload: bytes) -> bytes: ...


class Ed25519FileSigner:
    def __init__(self, key_id: str, private_key: Ed25519PrivateKey):
        self._key_id = key_id
        self._private_key = private_key

    @classmethod
    def from_file(cls, key_id: str, path: str | Path) -> "Ed25519FileSigner":
        try:
            return cls(key_id, load_private_key(Path(path)))
        except (OSError, ValueError) as exc:
            raise KeyError("Provider private key could not be loaded.") from exc

    @property
    def key_id(self) -> str:
        return self._key_id

    @property
    def public_key_base64(self) -> str:
        return encode_public_key(self._private_key.public_key())

    def sign(self, payload: bytes) -> bytes:
        return self._private_key.sign(payload)

    def __repr__(self) -> str:
        return f"Ed25519FileSigner(key_id={self.key_id!r})"


class GapProvider:
    def __init__(self, provider_identity: ProviderIdentity, signer: CredentialSigner):
        self.identity = ProviderIdentity.model_validate(provider_identity)
        self.signer = signer
        key = next(
            (item for item in self.identity.keys if item.key_id == signer.key_id), None
        )
        if key is None or self.identity.active_key_id != signer.key_id:
            raise KeyError("Signer does not match the provider active key.")
        if key.status != "active":
            raise KeyError("The provider signing key is not active.")
        public_key = getattr(signer, "public_key_base64", None)
        if public_key is not None and public_key != key.public_key:
            raise KeyError("Provider private and public keys do not match.")

    @classmethod
    def from_key_file(
        cls,
        provider_identity: ProviderIdentity | dict,
        private_key_path: str | Path,
    ) -> "GapProvider":
        identity = ProviderIdentity.model_validate(provider_identity)
        return cls(
            identity,
            Ed25519FileSigner.from_file(identity.active_key_id, private_key_path),
        )

    def issue_credential(
        self,
        artifact: bytes,
        generation_context: GenerationContext | dict,
        *,
        binding_profile: str = RAW_BINDING,
    ) -> GenerationCredential:
        context = GenerationContext.model_validate(generation_context)
        if binding_profile == RAW_BINDING:
            digest = hashlib.sha256(artifact).hexdigest()
        else:
            from .interop import PNG_BINDING
            from .media import calculate_png_binding_digest

            if binding_profile != PNG_BINDING:
                raise CredentialError(
                    f"Unsupported binding profile: {binding_profile}."
                )
            digest = calculate_png_binding_digest(artifact)
        payload = self._payload(digest, context, binding_profile)
        signature = base64.b64encode(
            self.signer.sign(canonicalise_model(payload))
        ).decode("ascii")
        return GenerationCredential(
            payload=payload,
            proof=GenerationCredentialProof(
                key_id=self.signer.key_id, signature=signature
            ),
        )

    def issue_credential_for_file(
        self,
        path: str | Path,
        generation_context: GenerationContext | dict,
        *,
        binding_profile: str = RAW_BINDING,
    ) -> GenerationCredential:
        context = GenerationContext.model_validate(generation_context)
        if binding_profile == RAW_BINDING:
            digest = sha256_file(path)
        else:
            from .interop import PNG_BINDING
            from .media import calculate_png_binding_digest

            if binding_profile != PNG_BINDING:
                raise CredentialError(
                    f"Unsupported binding profile: {binding_profile}."
                )
            digest = calculate_png_binding_digest(Path(path).read_bytes())
        payload = self._payload(digest, context, binding_profile)
        signature = base64.b64encode(
            self.signer.sign(canonicalise_model(payload))
        ).decode("ascii")
        return GenerationCredential(
            payload=payload,
            proof=GenerationCredentialProof(
                key_id=self.signer.key_id, signature=signature
            ),
        )

    def _payload(
        self, digest: str, context: GenerationContext, binding_profile: str
    ) -> GenerationCredentialPayload:
        created_at = context.created_at
        if created_at.tzinfo is None:
            raise CredentialError("Generation timestamp must be timezone-aware.")
        generation_id = context.request_id or f"gid-{uuid4()}"
        return GenerationCredentialPayload(
            credential_id=f"gc-{uuid4()}",
            generation=CredentialGeneration(
                generation_id=generation_id,
                created_at=created_at.astimezone(timezone.utc),
            ),
            provider=CredentialProvider(provider_id=self.identity.provider_id),
            model=CredentialModel(model_id=context.model),
            artifacts=[
                ArtifactDescriptor(
                    media_type=context.media_type,
                    digest=ArtifactDigest(value=digest),
                    binding_profile=binding_profile,
                )
            ],
        )

    def save_credential(
        self,
        artifact_path: str | Path,
        credential: GenerationCredential,
        *,
        overwrite: bool = False,
    ) -> Path:
        return write_sidecar(artifact_path, credential, overwrite=overwrite)

    def load_credential(self, artifact_path: str | Path) -> GenerationCredential:
        return read_sidecar(artifact_path)

    def verify_own_credential(self, credential: GenerationCredential) -> bool:
        return verify_generation_credential(credential, self.identity)

    def __repr__(self) -> str:
        return f"GapProvider(provider_id={self.identity.provider_id!r}, key_id={self.signer.key_id!r})"
