from __future__ import annotations

import hashlib
from pathlib import Path
from typing import BinaryIO

from app.schemas.provider_identity import ProviderIdentityDocument
from app.services.verification_service import verify_generation_credential_details

from .client import GapServiceClient
from .errors import CredentialError
from .files import sha256_file
from .models import (
    CheckStatus,
    GapCredential,
    TrustMaterialBundle,
    VerificationCheck,
    VerificationLevel,
    VerificationResult,
)
from .offline import evaluate_offline_full
from .interop import PNG_BINDING, RAW_BINDING, signed_binding_profile


class GapVerifier:
    def __init__(
        self,
        *,
        client: GapServiceClient | None = None,
        trust_material: TrustMaterialBundle | None = None,
        maximum_trust_material_age_seconds: int = 24 * 60 * 60,
    ):
        self.client = client
        self.trust_material = trust_material
        self.maximum_trust_material_age_seconds = maximum_trust_material_age_seconds

    @classmethod
    def from_service(cls, base_url: str, **kwargs) -> "GapVerifier":
        return cls(client=GapServiceClient(base_url, **kwargs))

    @classmethod
    def from_trust_material(
        cls,
        trust_material: TrustMaterialBundle | dict,
        *,
        maximum_age_seconds: int = 24 * 60 * 60,
    ) -> "GapVerifier":
        from .trust import validate_trust_material

        material = TrustMaterialBundle.model_validate(trust_material)
        validate_trust_material(material)
        return cls(
            trust_material=material,
            maximum_trust_material_age_seconds=maximum_age_seconds,
        )

    @classmethod
    def from_local_files(cls, trust_material_path: str | Path) -> "GapVerifier":
        from .trust import load_trust_material

        return cls(trust_material=load_trust_material(trust_material_path))

    def verify(
        self,
        artifact: bytes | str | Path | BinaryIO,
        credential: GapCredential | dict,
        *,
        level: VerificationLevel = VerificationLevel.FULL,
    ) -> VerificationResult:
        try:
            credential = GapCredential.model_validate(credential)
        except ValueError as exc:
            raise CredentialError("Credential is malformed.") from exc
        profile = signed_binding_profile(credential)
        if profile == RAW_BINDING:
            actual_digest = self._digest(artifact)
        elif profile == PNG_BINDING:
            from .media import calculate_png_binding_digest

            actual_digest = calculate_png_binding_digest(self._read_bytes(artifact))
        else:
            raise CredentialError(f"Unsupported signed binding profile: {profile}.")
        expected_digest = credential.payload.artifacts[0].digest.value
        integrity = actual_digest == expected_digest
        checks = [
            VerificationCheck(
                code="artifact-digest",
                name="Artifact integrity",
                status=CheckStatus.PASSED if integrity else CheckStatus.FAILED,
                summary="Artifact digest matches."
                if integrity
                else "Artifact digest does not match.",
            )
        ]
        provider_id = credential.payload.provider.provider_id
        response = None
        crypto = False
        if self.client:
            response = self.client.verify_credential(credential)
            crypto = bool(response.get("cryptographic_valid"))
        elif self.trust_material:
            provider = next(
                (
                    item
                    for item in self.trust_material.state.get("providers", [])
                    if item.get("provider_id") == provider_id
                ),
                None,
            )
            if provider:
                crypto = verify_generation_credential_details(
                    credential, ProviderIdentityDocument.model_validate(provider)
                ).valid
        checks.append(
            VerificationCheck(
                code="provider-signature",
                name="Provider signature",
                status=CheckStatus.PASSED if crypto else CheckStatus.FAILED,
                summary="Provider signature is valid."
                if crypto
                else "Provider signature is invalid or its key is unavailable.",
            )
        )
        if level == VerificationLevel.CRYPTOGRAPHIC:
            valid = integrity and crypto
            return self._result(credential, actual_digest, level, level, valid, checks)
        if response is None and self.trust_material:
            from datetime import datetime, timezone

            exported_at = self.trust_material.state.get("exported_at")
            if exported_at:
                exported = datetime.fromisoformat(
                    str(exported_at).replace("Z", "+00:00")
                )
                if (
                    datetime.now(timezone.utc) - exported
                ).total_seconds() > self.maximum_trust_material_age_seconds:
                    checks.append(
                        VerificationCheck(
                            code="trust-material-freshness",
                            name="Trust material freshness",
                            status=CheckStatus.FAILED,
                            summary="Trust material is stale.",
                        )
                    )
                    return self._result(
                        credential,
                        actual_digest,
                        level,
                        VerificationLevel.CRYPTOGRAPHIC if crypto else None,
                        False,
                        checks,
                        failure="stale-trust-material",
                        missing=["current public trust evidence"],
                    )
            response = evaluate_offline_full(credential, self.trust_material.state)
            if response.get("incomplete"):
                checks.append(
                    VerificationCheck(
                        code="trust-evidence",
                        name="Offline trust evidence",
                        status=CheckStatus.UNAVAILABLE,
                        summary="Complete offline trust evidence is unavailable.",
                        technical_detail=response.get("failure_reason"),
                    )
                )
                return self._result(
                    credential,
                    actual_digest,
                    level,
                    VerificationLevel.CRYPTOGRAPHIC if crypto else None,
                    False,
                    checks,
                    failure="incomplete-verification",
                    missing=[response.get("failure_reason") or "full public evidence"],
                )
        if response is None:
            checks.append(
                VerificationCheck(
                    code="trust-evidence",
                    name="Provider trust",
                    status=CheckStatus.UNAVAILABLE,
                    summary="Complete offline trust evidence could not be evaluated.",
                )
            )
            return self._result(
                credential,
                actual_digest,
                level,
                VerificationLevel.CRYPTOGRAPHIC if crypto else None,
                False,
                checks,
                failure="incomplete-verification",
                missing=["validated trust, transparency, witness and gossip evidence"],
            )
        provider_trusted = bool(response.get("provider_trusted"))
        full_fields = (
            "transparency_verified",
            "witness_quorum_met",
            "checkpoint_gossip_consistent",
        )
        for code, label in (
            ("provider_trusted", "Provider trust"),
            ("transparency_verified", "Transparency inclusion"),
            ("witness_quorum_met", "Witness quorum"),
            ("checkpoint_gossip_consistent", "Checkpoint gossip"),
        ):
            passed = bool(response.get(code))
            checks.append(
                VerificationCheck(
                    code=code.replace("_", "-"),
                    name=label,
                    status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
                    summary=f"{label} {'passed' if passed else 'failed'}.",
                    required_for_overall_validity=(
                        level == VerificationLevel.FULL or code == "provider_trusted"
                    ),
                )
            )
        trusted_valid = (
            integrity
            and crypto
            and provider_trusted
            and not response.get("federation_conflict")
        )
        if level == VerificationLevel.TRUSTED_PROVIDER:
            return self._result(
                credential,
                actual_digest,
                level,
                level,
                trusted_valid,
                checks,
                response=response,
            )
        valid = (
            integrity
            and bool(response.get("valid"))
            and all(response.get(f) for f in full_fields)
        )
        return self._result(
            credential,
            actual_digest,
            level,
            level
            if valid
            else VerificationLevel.TRUSTED_PROVIDER
            if trusted_valid
            else VerificationLevel.CRYPTOGRAPHIC
            if crypto
            else None,
            valid,
            checks,
            response=response,
        )

    @staticmethod
    def _digest(artifact: bytes | str | Path | BinaryIO) -> str:
        if isinstance(artifact, bytes):
            return hashlib.sha256(artifact).hexdigest()
        if isinstance(artifact, (str, Path)):
            return sha256_file(artifact)
        digest = hashlib.sha256()
        while chunk := artifact.read(1024 * 1024):
            digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _read_bytes(artifact: bytes | str | Path | BinaryIO) -> bytes:
        if isinstance(artifact, bytes):
            return artifact
        if isinstance(artifact, (str, Path)):
            return Path(artifact).read_bytes()
        return artifact.read()

    @staticmethod
    def _result(
        credential,
        digest,
        requested,
        achieved,
        valid,
        checks,
        *,
        response=None,
        failure=None,
        missing=None,
    ):
        response = response or {}
        failed = next(
            (check for check in checks if check.status == CheckStatus.FAILED), None
        )
        failure = failure or (failed.code if failed else None)
        return VerificationResult(
            valid=valid,
            requested_level=requested,
            achieved_level=achieved,
            credential_id=credential.payload.credential_id,
            provider_id=credential.payload.provider.provider_id,
            artifact_digest=digest,
            checks=checks,
            missing_evidence=missing or [],
            failure_code=failure,
            failure_message=None
            if valid
            else (failed.summary if failed else "Verification is incomplete."),
            summary="GAP verification passed."
            if valid
            else "GAP verification did not pass.",
            artifact_integrity_valid=checks[0].status == CheckStatus.PASSED,
            cryptographic_valid=bool(
                response.get(
                    "cryptographic_valid", checks[1].status == CheckStatus.PASSED
                )
            ),
            provider_trusted=bool(response.get("provider_trusted")),
            federation_state_valid=not bool(response.get("federation_conflict")),
            transparency_verified=bool(response.get("transparency_verified")),
            witness_quorum_met=bool(response.get("witness_quorum_met")),
            checkpoint_gossip_consistent=bool(
                response.get("checkpoint_gossip_consistent")
            ),
            federation_conflict=bool(response.get("federation_conflict")),
            split_view_detected=bool(response.get("split_view_detected")),
            witness_equivocation_detected=bool(
                response.get("witness_equivocation_detected")
            ),
        )
