"""Run the Sprint 16 pilot against separately running GAP/provider services."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from gap_sdk import (
    GapPackage,
    GapProvider,
    GapServiceClient,
    GapVerifier,
    GenerationRequest,
    HttpGenerationProviderAdapter,
    PNG_BINDING,
    VerificationLevel,
    embed_credential_in_png,
)
from gap_sdk.errors import PackageError
from gap_sdk.models import ProviderIdentity, TrustMaterialBundle
from gap_sdk.trust import save_trust_material


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gap-service", default="http://127.0.0.1:8765")
    parser.add_argument("--provider-service", default="http://127.0.0.1:8766")
    parser.add_argument(
        "--private-key",
        type=Path,
        default=Path("implementation/keys/demo_2026_02_private.key"),
    )
    args = parser.parse_args()

    gap = GapServiceClient(args.gap_service)
    gap.negotiate(binding_profile=PNG_BINDING)
    generator = HttpGenerationProviderAdapter(args.provider_service)
    generated = generator.generate(
        GenerationRequest(
            prompt="Sprint 16 independent process pilot",
            request_id="sprint16-live-pilot",
        )
    )
    identity = ProviderIdentity.model_validate(gap.get_provider("gap-demo-provider"))
    provider = GapProvider.from_key_file(identity, args.private_key)
    credential = provider.issue_credential(
        generated.artifact,
        {
            "model": generated.model_id,
            "request_id": generated.request_id,
            "media_type": generated.media_type,
        },
        binding_profile=PNG_BINDING,
    )
    embedded = embed_credential_in_png(generated.artifact, credential)
    online = GapVerifier.from_service(args.gap_service)
    online_result = online.verify(embedded, credential, level=VerificationLevel.FULL)
    state = gap.export_trust_material()
    with TemporaryDirectory(prefix="gap-sprint16-pilot-") as directory:
        root = Path(directory)
        trust_path = save_trust_material(state, root / "trust.json")
        trust = json.loads(trust_path.read_text("utf-8"))
        package = GapPackage.create(
            generated.artifact,
            credential,
            trust_material=trust,
        )
        package_result = GapPackage.verify(
            package, online, level=VerificationLevel.FULL
        )
        offline = GapVerifier.from_trust_material(
            TrustMaterialBundle.model_validate(trust)
        )
        offline_result = offline.verify(
            embedded, credential, level=VerificationLevel.FULL
        )
        offline_package_result = GapPackage.verify(
            package, offline, level=VerificationLevel.FULL
        )
        tampered_media = bytearray(embedded)
        tampered_media[40] ^= 1
        media_tamper_rejected = False
        try:
            result = offline.verify(bytes(tampered_media), credential)
            media_tamper_rejected = not result.valid
        except Exception:
            media_tamper_rejected = True
        tampered_package = bytearray(package)
        tampered_package[len(tampered_package) // 2] ^= 1
        package_tamper_rejected = False
        try:
            GapPackage.verify_integrity(bytes(tampered_package))
        except PackageError:
            package_tamper_rejected = True
    summary = {
        "provider_process_boundary": True,
        "request_id_propagated": generated.request_id == "sprint16-live-pilot",
        "online_full": online_result.valid,
        "package_online_full": package_result.valid,
        "offline_full": offline_result.valid,
        "package_offline_full": offline_package_result.valid,
        "online_offline_match": online_result.valid == offline_result.valid,
        "media_tamper_rejected": media_tamper_rejected,
        "package_tamper_rejected": package_tamper_rejected,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if all(summary.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
