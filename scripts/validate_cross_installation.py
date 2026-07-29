"""Validate portable GAP verification across isolated persistent installations."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "implementation"))

from gap_sdk import (  # noqa: E402
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
from gap_sdk.models import ProviderIdentity  # noqa: E402
from gap_sdk.trust import save_trust_material  # noqa: E402

EQUIVALENCE_FIELDS = (
    "valid",
    "artifact_integrity_valid",
    "cryptographic_valid",
    "provider_trusted",
    "federation_state_valid",
    "transparency_verified",
    "witness_quorum_met",
    "checkpoint_gossip_consistent",
    "federation_conflict",
    "split_view_detected",
    "witness_equivocation_detected",
    "achieved_level",
    "failure_code",
)


def enforce_isolation(
    database_a: str | Path,
    database_b: str | Path,
    runtime_a: str | Path,
    runtime_b: str | Path,
    port_a: int,
    port_b: int,
) -> None:
    if Path(database_a).resolve() == Path(database_b).resolve():
        raise ValueError("Instances must use distinct database files.")
    if Path(runtime_a).resolve() == Path(runtime_b).resolve():
        raise ValueError("Instances must use distinct runtime directories.")
    if port_a == port_b:
        raise ValueError("Instances must use distinct ports.")


def equivalent_results(*results: dict[str, Any]) -> bool:
    normalized = [
        {field: result.get(field) for field in EQUIVALENCE_FIELDS} for result in results
    ]
    return all(item == normalized[0] for item in normalized[1:])


def redact_path(path: Path, label: str) -> dict[str, str]:
    return {
        "label": label,
        "identity_sha256": hashlib.sha256(
            str(path.resolve()).encode("utf-8")
        ).hexdigest(),
    }


def database_counts(path: Path) -> dict[str, int]:
    with sqlite3.connect(path) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in tables
        }


def _wait(url: str, process: subprocess.Popen, timeout: float = 20) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Process exited while waiting for {url}.")
        try:
            response = httpx.get(url, timeout=1)
            if response.status_code == 200:
                return response.json()
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise TimeoutError(f"Timed out waiting for {url}.")


def _start(command: list[str], cwd: Path, env: dict, log_path: Path):
    log = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    return process, log


def _stop(process: subprocess.Popen | None, log) -> None:
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    if log:
        log.close()


def _portable_verify(
    base_url: str, artifact: bytes, credential: dict, trust: dict
) -> tuple[int, dict]:
    response = httpx.post(
        f"{base_url}/portable/verify",
        json={
            "artifact_base64": base64.b64encode(artifact).decode("ascii"),
            "credential": credential,
            "trust_material": trust,
            "level": "full",
        },
        timeout=20,
    )
    try:
        body = response.json()
    except ValueError:
        body = {}
    return response.status_code, body


def run(port_a: int = 8775, port_b: int = 8776, provider_port: int = 8777):
    python = ROOT / ".venv" / "Scripts" / "python.exe"
    with tempfile.TemporaryDirectory(prefix="gap-cross-installation-") as temp:
        root = Path(temp)
        database_a = root / "instance-a" / "gap-a.db"
        database_b = root / "instance-b" / "gap-b.db"
        runtime_a = root / "instance-a" / "runtime"
        runtime_b = root / "instance-b" / "runtime"
        transfer = root / "transfer"
        for directory in (
            database_a.parent,
            database_b.parent,
            runtime_a,
            runtime_b,
            transfer,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        enforce_isolation(database_a, database_b, runtime_a, runtime_b, port_a, port_b)
        env_a = os.environ.copy()
        env_a.update(
            {
                "APP_ENV": "test",
                "PERSISTENCE_MODE": "database",
                "DATABASE_URL": f"sqlite:///{database_a.as_posix()}",
                "RUNTIME_DIRECTORY": str(runtime_a),
                "KEY_DIRECTORY": str(ROOT / "implementation" / "keys"),
            }
        )
        env_b = os.environ.copy()
        env_b.update(
            {
                "GAP_VERIFIER_DATABASE": str(database_b),
                "GAP_VERIFIER_RUNTIME": str(runtime_b),
            }
        )
        subprocess.run(
            [str(python), str(ROOT / "scripts" / "manage_database.py"), "upgrade"],
            cwd=ROOT,
            env=env_a,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        processes: list[tuple[subprocess.Popen, Any]] = []
        process_a = process_b = process_provider = None
        try:
            process_a, log_a = _start(
                [
                    str(python),
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port_a),
                ],
                ROOT / "implementation",
                env_a,
                root / "instance-a.log",
            )
            processes.append((process_a, log_a))
            process_b, log_b = _start(
                [
                    str(python),
                    "-m",
                    "uvicorn",
                    "examples.portable_verifier_service:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port_b),
                ],
                ROOT,
                env_b,
                root / "instance-b.log",
            )
            processes.append((process_b, log_b))
            process_provider, log_provider = _start(
                [
                    str(python),
                    "-m",
                    "uvicorn",
                    "examples.external_provider_service:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(provider_port),
                ],
                ROOT,
                os.environ.copy(),
                root / "provider.log",
            )
            processes.append((process_provider, log_provider))
            health_a = _wait(f"http://127.0.0.1:{port_a}/health/ready", process_a)
            _wait(f"http://127.0.0.1:{port_b}/health/ready", process_b)
            _wait(
                f"http://127.0.0.1:{provider_port}/.well-known/generation-provider.json",
                process_provider,
            )
            client_a = GapServiceClient(f"http://127.0.0.1:{port_a}")
            head_before = client_a._request("GET", "/transparency/tree-head")
            quorum_before = client_a._request("GET", "/transparency/witness-quorum")
            generator = HttpGenerationProviderAdapter(
                f"http://127.0.0.1:{provider_port}"
            )
            generated = generator.generate(
                GenerationRequest(
                    prompt="Cross-installation Sprint 16 validation",
                    request_id="sprint16-cross-installation",
                )
            )
            identity = ProviderIdentity.model_validate(
                client_a.get_provider("gap-demo-provider")
            )
            provider = GapProvider.from_key_file(
                identity,
                ROOT / "implementation" / "keys" / "demo_2026_02_private.key",
            )
            credential = provider.issue_credential(
                generated.artifact,
                {
                    "model": generated.model_id,
                    "request_id": generated.request_id,
                    "media_type": generated.media_type,
                },
                binding_profile=PNG_BINDING,
            )
            artifact_path = transfer / "artifact.png"
            artifact_path.write_bytes(generated.artifact)
            sidecar_path = provider.save_credential(artifact_path, credential)
            embedded = embed_credential_in_png(generated.artifact, credential)
            embedded_path = transfer / "artifact-embedded.png"
            embedded_path.write_bytes(embedded)
            state = client_a.export_trust_material()
            trust_path = save_trust_material(state, transfer / "trust-material.json")
            trust = json.loads(trust_path.read_text("utf-8"))
            package_path = GapPackage.create(
                generated.artifact,
                credential,
                transfer / "artifact.gapbundle",
                trust_material=trust,
            )
            online = GapVerifier.from_service(f"http://127.0.0.1:{port_a}")
            result_a = online.verify(
                embedded, credential, level=VerificationLevel.FULL
            ).model_dump(mode="json", exclude_none=True)
            result_sidecar_a = online.verify(
                generated.artifact, credential, level=VerificationLevel.FULL
            )
            result_package_a = GapPackage.verify(
                package_path, online, level=VerificationLevel.FULL
            )
            offline = GapVerifier.from_trust_material(trust)
            result_offline = offline.verify(
                embedded, credential, level=VerificationLevel.FULL
            ).model_dump(mode="json", exclude_none=True)
            status_b, result_b = _portable_verify(
                f"http://127.0.0.1:{port_b}",
                embedded,
                credential.model_dump(mode="json", exclude_none=True),
                trust,
            )
            if status_b != 200:
                raise RuntimeError("Instance B portable verification failed.")
            three_way = equivalent_results(result_a, result_offline, result_b)
            if not (
                result_a["valid"]
                and result_offline["valid"]
                and result_b["valid"]
                and result_package_a.valid
                and result_sidecar_a.valid
                and three_way
            ):
                raise RuntimeError("Three-way FULL verification did not match.")

            tampering = {}
            tampered_artifact = bytearray(embedded)
            tampered_artifact[40] ^= 1
            status, body = _portable_verify(
                f"http://127.0.0.1:{port_b}",
                bytes(tampered_artifact),
                credential.model_dump(mode="json", exclude_none=True),
                trust,
            )
            tampering["artifact"] = status != 200 or not body.get("valid", False)
            tampered_credential_png = bytearray(embedded)
            gap_offset = tampered_credential_png.index(b"gaPc") + 4
            tampered_credential_png[gap_offset] ^= 1
            status, _ = _portable_verify(
                f"http://127.0.0.1:{port_b}",
                bytes(tampered_credential_png),
                credential.model_dump(mode="json", exclude_none=True),
                trust,
            )
            tampering["embedded_credential"] = status == 422
            unknown = credential.model_dump(mode="json", exclude_none=True)
            unknown["payload"]["artifacts"][0]["binding_profile"] = "gap-unknown-v1"
            status, _ = _portable_verify(
                f"http://127.0.0.1:{port_b}", embedded, unknown, trust
            )
            tampering["unknown_profile"] = status == 422
            downgrade = credential.model_dump(mode="json", exclude_none=True)
            downgrade["payload"]["artifacts"][0]["binding_profile"] = "gap-raw-bytes-v1"
            status, body = _portable_verify(
                f"http://127.0.0.1:{port_b}", embedded, downgrade, trust
            )
            tampering["downgrade"] = status != 200 or not body.get("valid", False)
            corrupt_trust = json.loads(json.dumps(trust))
            corrupt_trust["state"]["providers"] = []
            status, _ = _portable_verify(
                f"http://127.0.0.1:{port_b}",
                embedded,
                credential.model_dump(mode="json", exclude_none=True),
                corrupt_trust,
            )
            tampering["corrupt_trust"] = status == 422
            raw_package = bytearray(Path(package_path).read_bytes())
            raw_package[len(raw_package) // 2] ^= 1
            try:
                GapPackage.verify_integrity(bytes(raw_package))
                tampering["package"] = False
            except Exception:
                tampering["package"] = True
            package_members = GapPackage.open(package_path)
            package_stream = BytesIO()
            with zipfile.ZipFile(package_stream, "w") as archive:
                for name, value in package_members.items():
                    archive.writestr(
                        name,
                        value.replace(b"gap-package-v1", b"gap-package-x1")
                        if name == "manifest.json"
                        else value,
                    )
            try:
                GapPackage.verify_integrity(package_stream.getvalue())
                tampering["manifest"] = False
            except Exception:
                tampering["manifest"] = True
            stale_state = json.loads(json.dumps(state))
            stale_state["exported_at"] = "2000-01-01T00:00:00Z"
            stale_path = save_trust_material(
                stale_state, transfer / "stale-trust-material.json"
            )
            stale_trust = json.loads(stale_path.read_text("utf-8"))
            status, body = _portable_verify(
                f"http://127.0.0.1:{port_b}",
                embedded,
                credential.model_dump(mode="json", exclude_none=True),
                stale_trust,
            )
            tampering["stale_trust"] = (
                status == 200
                and not body.get("valid", False)
                and body.get("failure_code") == "stale-trust-material"
            )
            if not all(tampering.values()):
                raise RuntimeError("Instance B tampering checks did not fail closed.")

            counts_a = database_counts(database_a)
            counts_b = database_counts(database_b)
            if any("trust" in table for table in counts_b):
                raise RuntimeError("Instance B persisted Instance A trust rows.")

            _stop(process_b, log_b)
            processes.remove((process_b, log_b))
            process_b, log_b = _start(
                [
                    str(python),
                    "-m",
                    "uvicorn",
                    "examples.portable_verifier_service:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port_b),
                ],
                ROOT,
                env_b,
                root / "instance-b-restart.log",
            )
            processes.append((process_b, log_b))
            _wait(f"http://127.0.0.1:{port_b}/health/ready", process_b)
            status, result_b_restart = _portable_verify(
                f"http://127.0.0.1:{port_b}",
                embedded,
                credential.model_dump(mode="json", exclude_none=True),
                trust,
            )
            b_restart = status == 200 and equivalent_results(result_b, result_b_restart)

            _stop(process_a, log_a)
            processes.remove((process_a, log_a))
            process_a, log_a = _start(
                [
                    str(python),
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port_a),
                ],
                ROOT / "implementation",
                env_a,
                root / "instance-a-restart.log",
            )
            processes.append((process_a, log_a))
            _wait(f"http://127.0.0.1:{port_a}/health/ready", process_a)
            restarted_a = GapServiceClient(f"http://127.0.0.1:{port_a}")
            head_after = restarted_a._request("GET", "/transparency/tree-head")
            quorum_after = restarted_a._request("GET", "/transparency/witness-quorum")
            result_a_restart = (
                GapVerifier.from_service(f"http://127.0.0.1:{port_a}")
                .verify(embedded, credential, level=VerificationLevel.FULL)
                .model_dump(mode="json", exclude_none=True)
            )
            a_restart = (
                head_before == head_after
                and quorum_before == quorum_after
                and equivalent_results(result_a, result_a_restart)
            )
            if not b_restart or not a_restart:
                raise RuntimeError("Persistence restart validation failed.")
            report = {
                "format": "gap-cross-installation-validation-v1",
                "version": health_a["version"],
                "passed": True,
                "instance_a": {
                    "pid": process_a.pid,
                    "port": port_a,
                    "database": redact_path(database_a, "instance-a-database"),
                    "runtime": redact_path(runtime_a, "instance-a-runtime"),
                    "database_sha256": hashlib.sha256(
                        database_a.read_bytes()
                    ).hexdigest(),
                    "record_counts": counts_a,
                },
                "instance_b": {
                    "pid": process_b.pid,
                    "port": port_b,
                    "database": redact_path(database_b, "instance-b-database"),
                    "runtime": redact_path(runtime_b, "instance-b-runtime"),
                    "database_sha256": hashlib.sha256(
                        database_b.read_bytes()
                    ).hexdigest(),
                    "record_counts": counts_b,
                    "contains_instance_a_trust_rows": False,
                },
                "process_isolation": process_a.pid != process_b.pid,
                "database_isolation": database_a.resolve() != database_b.resolve(),
                "runtime_isolation": runtime_a.resolve() != runtime_b.resolve(),
                "transferred_files": [
                    artifact_path.name,
                    sidecar_path.name,
                    embedded_path.name,
                    Path(package_path).name,
                    trust_path.name,
                ],
                "instance_a_online_full": result_a["valid"],
                "offline_sdk_full": result_offline["valid"],
                "instance_b_full": result_b["valid"],
                "three_way_equivalent": three_way,
                "instance_b_restart": b_restart,
                "instance_a_restart": a_restart,
                "tampering_rejected": tampering,
                "private_state_transferred": False,
            }
            return report
        finally:
            for process, log in reversed(processes):
                _stop(process, log)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port-a", type=int, default=8775)
    parser.add_argument("--port-b", type=int, default=8776)
    parser.add_argument("--provider-port", type=int, default=8777)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        report = run(args.port_a, args.port_b, args.provider_port)
    except Exception as exc:
        report = {
            "format": "gap-cross-installation-validation-v1",
            "passed": False,
            "error": str(exc),
        }
    print(
        json.dumps(report, sort_keys=True)
        if args.json
        else json.dumps(report, indent=2, sort_keys=True)
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
