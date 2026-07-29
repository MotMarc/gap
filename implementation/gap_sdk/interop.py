from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .errors import CompatibilityError

PROTOCOL_PROFILE = "gap-interop-v1"
CREDENTIAL_SCHEMA = "gap-credential-v1"
RAW_BINDING = "gap-raw-bytes-v1"
PNG_BINDING = "gap-png-embedded-v1"
SIDECAR_FORMAT = "gap-sidecar-v1"
PACKAGE_FORMAT = "gap-package-v1"
TRUST_FORMAT = "gap-public-state-v2"
DIGEST_ALGORITHM = "sha-256"

MAX_CREDENTIAL_SIZE = 256 * 1024
MAX_EMBEDDED_METADATA_SIZE = 256 * 1024
MAX_PACKAGE_SIZE = 100 * 1024 * 1024


class GapServiceCapabilities(BaseModel):
    service_id: str
    application_version: str
    interoperability_profiles: list[str]
    protocol_object_versions: dict[str, list[str]]
    credential_schemas: list[str]
    binding_profiles: list[str]
    digest_algorithms: list[str]
    trust_material_formats: list[str]
    verification_levels: list[str]
    public_endpoints: dict[str, str]
    maximum_credential_size: int = Field(gt=0)
    maximum_package_size: int = Field(gt=0)
    maximum_embedded_metadata_size: int = Field(gt=0)
    server_time: datetime
    documentation: str | None = None
    discovery_is_trust_root: Literal[False] = False

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def declarations_are_consistent(self):
        if (
            PNG_BINDING in self.binding_profiles
            and CREDENTIAL_SCHEMA not in self.credential_schemas
        ):
            raise ValueError("PNG binding requires the v1 credential schema.")
        if self.maximum_embedded_metadata_size > self.maximum_credential_size:
            raise ValueError("Embedded metadata limit exceeds credential limit.")
        return self


class NegotiatedCapabilities(BaseModel):
    interoperability_profile: str
    credential_schema: str
    binding_profile: str
    digest_algorithm: str
    trust_material_format: str
    verification_level: str


def negotiate(
    capabilities: GapServiceCapabilities | dict,
    *,
    binding_profile: str = RAW_BINDING,
    digest_algorithm: str = DIGEST_ALGORITHM,
    credential_schema: str = CREDENTIAL_SCHEMA,
    trust_material_format: str = TRUST_FORMAT,
    verification_level: str = "full",
) -> NegotiatedCapabilities:
    try:
        document = GapServiceCapabilities.model_validate(capabilities)
    except ValueError as exc:
        raise CompatibilityError("Contradictory capability declaration.") from exc
    checks = (
        (PROTOCOL_PROFILE, document.interoperability_profiles, "profile"),
        (credential_schema, document.credential_schemas, "credential schema"),
        (binding_profile, document.binding_profiles, "binding profile"),
        (digest_algorithm, document.digest_algorithms, "digest algorithm"),
        (trust_material_format, document.trust_material_formats, "trust material"),
        (verification_level, document.verification_levels, "verification level"),
    )
    for requested, supported, label in checks:
        if requested not in supported:
            raise CompatibilityError(f"Unsupported {label}: {requested}.")
    return NegotiatedCapabilities(
        interoperability_profile=PROTOCOL_PROFILE,
        credential_schema=credential_schema,
        binding_profile=binding_profile,
        digest_algorithm=digest_algorithm,
        trust_material_format=trust_material_format,
        verification_level=verification_level,
    )


def signed_binding_profile(credential) -> str:
    profile = credential.payload.artifacts[0].binding_profile
    return profile or RAW_BINDING
