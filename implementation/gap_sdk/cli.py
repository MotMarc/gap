from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import GapProvider, GapServiceClient, GapVerifier, VerificationLevel, __version__
from .errors import GapError, NetworkError, ServiceError
from .models import GapCredential, ProviderIdentity
from .trust import load_trust_material
from .interop import PNG_BINDING
from .media import embed_credential_in_png, extract_credential_from_png
from .package import GapPackage
from .conformance import ConformanceCase, create_report


EXIT_SUCCESS, EXIT_GENERAL, EXIT_USAGE, EXIT_MALFORMED = 0, 1, 2, 3
EXIT_ARTIFACT, EXIT_CRYPTOGRAPHIC, EXIT_TRUST = 4, 5, 6
EXIT_TRANSPARENCY, EXIT_WITNESS, EXIT_SERVICE, EXIT_INCOMPLETE = 7, 8, 9, 10
EXIT_VALID = EXIT_SUCCESS  # Backward-compatible public name.


def _issue_arguments(command):
    command.add_argument("artifact", type=Path)
    command.add_argument("--identity", required=True, type=Path)
    command.add_argument("--private-key", required=True, type=Path)
    command.add_argument("--model", required=True)
    command.add_argument("--media-type", default="application/octet-stream")
    command.add_argument("--overwrite", action="store_true")
    command.set_defaults(action="credential-issue")


def _doctor_arguments(command):
    command.add_argument("--identity", required=True, type=Path)
    command.add_argument("--private-key", required=True, type=Path)
    command.add_argument("--service")
    command.set_defaults(action="provider-doctor")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="gap", description="GAP integration toolkit")
    root.add_argument("--json", action="store_true", dest="json_output")
    commands = root.add_subparsers(required=True)
    commands.add_parser("version").set_defaults(action="version")

    credential = commands.add_parser("credential").add_subparsers(required=True)
    _issue_arguments(credential.add_parser("issue"))
    inspect = credential.add_parser("inspect")
    inspect.add_argument("credential", type=Path)
    inspect.set_defaults(action="credential-inspect")
    _issue_arguments(commands.add_parser("credential-issue"))
    inspect = commands.add_parser("credential-inspect")
    inspect.add_argument("credential", type=Path)
    inspect.set_defaults(action="credential-inspect")

    verify = commands.add_parser("verify")
    verify.add_argument("artifact", type=Path)
    verify.add_argument("credential", type=Path)
    source = verify.add_mutually_exclusive_group(required=True)
    source.add_argument("--service")
    source.add_argument("--trust-material", type=Path)
    verify.add_argument(
        "--level",
        choices=[item.value for item in VerificationLevel],
        default=VerificationLevel.FULL.value,
    )
    verify.set_defaults(action="verify")

    provider = commands.add_parser("provider").add_subparsers(required=True)
    _doctor_arguments(provider.add_parser("doctor"))
    _doctor_arguments(commands.add_parser("provider-doctor"))

    trust = commands.add_parser("trust").add_subparsers(required=True)
    export = trust.add_parser("export")
    export.add_argument("--service", required=True)
    export.add_argument("--output", required=True, type=Path)
    export.add_argument("--overwrite", action="store_true")
    export.set_defaults(action="trust-export")
    inspect = trust.add_parser("inspect")
    inspect.add_argument("path", type=Path)
    inspect.set_defaults(action="trust-inspect")
    inspect = commands.add_parser("trust-material-inspect")
    inspect.add_argument("path", type=Path)
    inspect.set_defaults(action="trust-inspect")

    diagnostics = commands.add_parser("diagnostics")
    diagnostics.add_argument("--service", required=True)
    diagnostics.set_defaults(action="diagnostics")

    package = commands.add_parser("package").add_subparsers(required=True)
    create = package.add_parser("create")
    create.add_argument("--artifact", required=True, type=Path)
    create.add_argument("--credential", required=True, type=Path)
    create.add_argument("--output", required=True, type=Path)
    create.add_argument("--trust-material", type=Path)
    create.add_argument("--overwrite", action="store_true")
    create.set_defaults(action="package-create")
    inspect = package.add_parser("inspect")
    inspect.add_argument("package", type=Path)
    inspect.set_defaults(action="package-inspect")
    verify_package = package.add_parser("verify")
    verify_package.add_argument("package", type=Path)
    verify_package.add_argument("--service")
    verify_package.add_argument("--trust-material", type=Path)
    verify_package.add_argument("--offline", action="store_true")
    verify_package.add_argument(
        "--level", choices=[item.value for item in VerificationLevel], default="full"
    )
    verify_package.set_defaults(action="package-verify")
    extract = package.add_parser("extract")
    extract.add_argument("package", type=Path)
    extract.add_argument("--destination", required=True, type=Path)
    extract.add_argument("--overwrite", action="store_true")
    extract.set_defaults(action="package-extract")

    media = commands.add_parser("media").add_subparsers(required=True)
    embed = media.add_parser("embed")
    embed.add_argument("--artifact", required=True, type=Path)
    embed.add_argument("--credential", required=True, type=Path)
    embed.add_argument("--output", required=True, type=Path)
    embed.add_argument("--overwrite", action="store_true")
    embed.set_defaults(action="media-embed")
    inspect = media.add_parser("inspect")
    inspect.add_argument("artifact", type=Path)
    inspect.set_defaults(action="media-inspect")
    extract_credential = media.add_parser("extract-credential")
    extract_credential.add_argument("artifact", type=Path)
    extract_credential.add_argument("--output", required=True, type=Path)
    extract_credential.add_argument("--overwrite", action="store_true")
    extract_credential.set_defaults(action="media-extract")
    media_verify = media.add_parser("verify")
    media_verify.add_argument("artifact", type=Path)
    media_source = media_verify.add_mutually_exclusive_group(required=True)
    media_source.add_argument("--service")
    media_source.add_argument("--trust-material", type=Path)
    media_verify.add_argument(
        "--level", choices=[item.value for item in VerificationLevel], default="full"
    )
    media_verify.set_defaults(action="media-verify")

    conformance = commands.add_parser("conformance").add_subparsers(required=True)
    for suite in ("provider", "verifier", "service"):
        command = conformance.add_parser(suite)
        command.add_argument("--service")
        command.add_argument("--output", type=Path)
        command.set_defaults(action="conformance", suite=suite)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        action = args.action
        if action == "version":
            data = {"name": "gap", "version": __version__}
        elif action == "credential-issue":
            identity = ProviderIdentity.model_validate_json(
                args.identity.read_text("utf-8")
            )
            provider = GapProvider.from_key_file(identity, args.private_key)
            credential = provider.issue_credential_for_file(
                args.artifact, {"model": args.model, "media_type": args.media_type}
            )
            path = provider.save_credential(
                args.artifact, credential, overwrite=args.overwrite
            )
            data = {
                "credential_id": credential.payload.credential_id,
                "sidecar": path.name,
            }
        elif action == "credential-inspect":
            data = _read_credential(args.credential).model_dump(
                mode="json", exclude_none=True
            )
        elif action == "verify":
            verifier = (
                GapVerifier.from_service(args.service)
                if args.service
                else GapVerifier.from_trust_material(
                    load_trust_material(args.trust_material)
                )
            )
            result = verifier.verify(
                args.artifact,
                _read_credential(args.credential),
                level=VerificationLevel(args.level),
            )
            _emit(result.model_dump(mode="json", exclude_none=True), args.json_output)
            return _verification_exit(result)
        elif action == "provider-doctor":
            identity = ProviderIdentity.model_validate_json(
                args.identity.read_text("utf-8")
            )
            provider = GapProvider.from_key_file(identity, args.private_key)
            test_credential = provider.issue_credential(
                b"GAP provider doctor", {"model": "gap-provider-doctor"}
            )
            data = {
                "healthy": provider.verify_own_credential(test_credential),
                "provider_id": identity.provider_id,
                "key_id": provider.signer.key_id,
                "checks": [
                    "identity-valid",
                    "active-key",
                    "key-pair-match",
                    "test-credential-valid",
                ],
            }
            if args.service:
                client = GapServiceClient(args.service)
                service_result = client.verify_credential(test_credential)
                data.update(
                    service_ready=client.health().get("status") == "healthy",
                    provider_trusted=service_result.get("provider_trusted"),
                    full_policy_available=service_result.get("valid"),
                )
                data["healthy"] = bool(
                    data["healthy"]
                    and data["service_ready"]
                    and data["full_policy_available"]
                )
        elif action == "trust-export":
            output = GapServiceClient(args.service).export_trust_material(
                args.output, overwrite=args.overwrite
            )
            data = {"exported": True, "output": output.name}
        elif action == "trust-inspect":
            material = load_trust_material(args.path)
            data = {
                "format": material.manifest.get("format"),
                "sha256": material.manifest.get("sha256"),
                "supported_level": material.state.get(
                    "supported_maximum_verification_level"
                ),
                "exported_at": material.state.get("exported_at"),
                "sections": sorted(material.state),
                "private_data_included": material.state.get("private_data_included"),
            }
        elif action == "diagnostics":
            client = GapServiceClient(args.service)
            health = client.health()
            discovery = client.discover()
            data = {
                "healthy": health.get("status") == "healthy",
                "version": health.get("version"),
                "interoperability_profiles": discovery.interoperability_profiles,
                "binding_profiles": discovery.binding_profiles,
            }
        elif action == "package-create":
            output = GapPackage.create(
                args.artifact,
                args.credential,
                args.output,
                trust_material=args.trust_material,
                overwrite=args.overwrite,
            )
            data = {"created": True, "output": output.name, "format": "gap-package-v1"}
        elif action == "package-inspect":
            data = GapPackage.inspect(args.package)
            data["integrity_valid"] = GapPackage.verify_integrity(args.package)
        elif action == "package-verify":
            if args.service:
                verifier = GapVerifier.from_service(args.service)
            elif args.trust_material:
                verifier = GapVerifier.from_trust_material(
                    load_trust_material(args.trust_material)
                )
            elif args.offline:
                members = GapPackage.open(args.package)
                try:
                    trust = json.loads(members["trust/trust-material.json"])
                    verifier = GapVerifier.from_trust_material(trust)
                except (KeyError, ValueError) as exc:
                    raise GapError(
                        "Package does not contain valid offline trust material."
                    ) from exc
            else:
                raise GapError(
                    "Package verification requires --service, --trust-material, or --offline."
                )
            result = GapPackage.verify(
                args.package, verifier, level=VerificationLevel(args.level)
            )
            _emit(result.model_dump(mode="json", exclude_none=True), args.json_output)
            return _verification_exit(result)
        elif action == "package-extract":
            files = GapPackage.extract(
                args.package, args.destination, overwrite=args.overwrite
            )
            data = {
                "extracted": True,
                "destination": str(args.destination),
                "file_count": len(files),
            }
        elif action == "media-embed":
            if args.output.exists() and not args.overwrite:
                raise GapError("Media output already exists.")
            output = embed_credential_in_png(
                args.artifact.read_bytes(), _read_credential(args.credential)
            )
            args.output.write_bytes(output)
            data = {
                "embedded": True,
                "output": args.output.name,
                "binding_profile": PNG_BINDING,
            }
        elif action == "media-inspect":
            credential = extract_credential_from_png(args.artifact.read_bytes())
            data = {
                "binding_profile": credential.payload.artifacts[0].binding_profile,
                "credential_id": credential.payload.credential_id[:20],
                "provider_id": credential.payload.provider.provider_id,
            }
        elif action == "media-extract":
            if args.output.exists() and not args.overwrite:
                raise GapError("Credential output already exists.")
            credential = extract_credential_from_png(args.artifact.read_bytes())
            args.output.write_text(
                json.dumps(credential.model_dump(mode="json"), indent=2, sort_keys=True)
                + "\n",
                "utf-8",
            )
            data = {"extracted": True, "output": args.output.name}
        elif action == "media-verify":
            verifier = (
                GapVerifier.from_service(args.service)
                if args.service
                else GapVerifier.from_trust_material(
                    load_trust_material(args.trust_material)
                )
            )
            raw = args.artifact.read_bytes()
            result = verifier.verify(
                raw,
                extract_credential_from_png(raw),
                level=VerificationLevel(args.level),
            )
            _emit(result.model_dump(mode="json", exclude_none=True), args.json_output)
            return _verification_exit(result)
        elif action == "conformance":
            cases = [
                ConformanceCase(
                    case_id=f"{args.suite}.sdk-version",
                    status="passed" if __version__ == "1.0.0" else "failed",
                )
            ]
            if args.service:
                try:
                    negotiated = GapServiceClient(args.service).negotiate()
                    cases.append(
                        ConformanceCase(
                            case_id=f"{args.suite}.service-negotiation",
                            status="passed"
                            if negotiated.verification_level == "full"
                            else "failed",
                        )
                    )
                except GapError:
                    cases.append(
                        ConformanceCase(
                            case_id=f"{args.suite}.service-negotiation",
                            status="failed",
                        )
                    )
            report = create_report(args.suite, cases)
            data = report.model_dump(mode="json", exclude_none=True)
            if args.output:
                if args.output.exists():
                    raise GapError("Conformance report output already exists.")
                args.output.write_text(
                    json.dumps(data, indent=2, sort_keys=True) + "\n", "utf-8"
                )
            _emit(data, args.json_output)
            return EXIT_SUCCESS if report.passed else EXIT_GENERAL
        _emit(data, args.json_output)
        return EXIT_SUCCESS if data.get("healthy", True) else EXIT_GENERAL
    except FileNotFoundError:
        return _error("A required file was not found.", EXIT_USAGE, args.json_output)
    except (NetworkError, ServiceError) as exc:
        return _error(str(exc), EXIT_SERVICE, args.json_output)
    except (GapError, ValueError, json.JSONDecodeError) as exc:
        return _error(str(exc), EXIT_MALFORMED, args.json_output)


def _read_credential(path: Path):
    raw = json.loads(path.read_text("utf-8"))
    return GapCredential.model_validate(raw.get("credential", raw))


def _verification_exit(result) -> int:
    if result.valid:
        return EXIT_SUCCESS
    if result.failure_code in {"incomplete-verification", "stale-trust-material"}:
        return EXIT_INCOMPLETE
    if not result.artifact_integrity_valid:
        return EXIT_ARTIFACT
    if not result.cryptographic_valid:
        return EXIT_CRYPTOGRAPHIC
    if result.federation_conflict or not result.provider_trusted:
        return EXIT_TRUST
    if not result.transparency_verified:
        return EXIT_TRANSPARENCY
    if (
        not result.witness_quorum_met
        or not result.checkpoint_gossip_consistent
        or result.split_view_detected
        or result.witness_equivocation_detected
    ):
        return EXIT_WITNESS
    return EXIT_GENERAL


def _emit(data, json_output: bool) -> None:
    if json_output:
        print(json.dumps(data, sort_keys=True, separators=(",", ":")))
    else:
        for key, value in data.items():
            print(f"{key}: {value}")


def _error(message: str, code: int, json_output: bool) -> int:
    payload = {"error": message, "exit_code": code}
    print(
        json.dumps(payload, sort_keys=True) if json_output else f"error: {message}",
        file=sys.stderr,
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
