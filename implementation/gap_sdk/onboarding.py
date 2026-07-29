from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from .errors import PackageError
from .interop import PNG_BINDING, RAW_BINDING
from .models import GapCredential, ProviderIdentity
from .serialization import canonical_json


def prepare_onboarding_package(
    identity: ProviderIdentity | dict,
    test_credential: GapCredential | dict,
    *,
    capabilities: dict | None = None,
) -> dict:
    identity = ProviderIdentity.model_validate(identity)
    credential = GapCredential.model_validate(test_credential)
    package = {
        "format": "gap-provider-onboarding-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider_identity": identity.model_dump(mode="json"),
        "capabilities": capabilities
        or {
            "binding_profiles": [RAW_BINDING, PNG_BINDING],
            "digest_algorithms": ["sha-256"],
        },
        "test_credential": credential.model_dump(mode="json"),
        "contains_private_key": False,
        "production_contact_included": False,
    }
    encoded = canonical_json(package)
    return {
        "manifest": {
            "format": "gap-provider-onboarding-v1",
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "size": len(encoded),
        },
        "application": package,
    }


def validate_onboarding_package(package: dict) -> None:
    try:
        application = package["application"]
        manifest = package["manifest"]
        encoded = canonical_json(application)
        if (
            manifest["format"] != "gap-provider-onboarding-v1"
            or manifest["sha256"] != hashlib.sha256(encoded).hexdigest()
            or manifest["size"] != len(encoded)
            or application.get("contains_private_key") is not False
            or application.get("production_contact_included") is not False
        ):
            raise ValueError
        text = json.dumps(application).casefold()
        if "begin private key" in text or "begin encrypted private key" in text:
            raise ValueError
    except (KeyError, TypeError, ValueError) as exc:
        raise PackageError(
            "Onboarding package is invalid or was tampered with."
        ) from exc
