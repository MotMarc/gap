import subprocess
from pathlib import Path

import pytest

from scripts.validate_browser_console import (
    _wait_for_debug_port,
    classify_http_failure,
    classify_runtime_event,
    redact_report,
)
from scripts.validate_cross_installation import (
    enforce_isolation,
    equivalent_results,
    redact_path,
)


def test_browser_exception_and_rejection_classification():
    assert (
        classify_runtime_event("Runtime.exceptionThrown", {"exceptionDetails": {}})
        == "uncaught-exception"
    )
    assert (
        classify_runtime_event("Runtime.consoleAPICalled", {"type": "error"})
        == "console-error"
    )
    assert (
        classify_runtime_event("Log.entryAdded", {"entry": {"level": "error"}})
        == "log-error"
    )


def test_optional_and_required_resource_classification():
    assert (
        classify_http_failure("http://gap.test/favicon.ico", "Other", 404) == "optional"
    )
    assert (
        classify_http_failure("http://gap.test/static/app.js", "Script", 404)
        == "required"
    )
    assert classify_http_failure("http://gap.test/health", "Fetch", 500) == "required"


def test_browser_report_redaction():
    report = redact_report(
        {
            "profile_path": "C:/private/browser",
            "message": "Authorization token leaked",
            "normal": "safe",
        }
    )
    assert report["profile_path"] == "<redacted>"
    assert report["message"] == "<redacted>"
    assert report["normal"] == "safe"


def test_browser_debug_timeout_when_process_exits(tmp_path):
    process = subprocess.Popen(
        ["cmd", "/c", "exit", "0"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    process.wait(timeout=5)
    with pytest.raises(RuntimeError, match="exited"):
        _wait_for_debug_port(tmp_path, process)


def test_distinct_database_runtime_and_port_guards(tmp_path):
    database_a = tmp_path / "a.db"
    database_b = tmp_path / "b.db"
    runtime_a = tmp_path / "runtime-a"
    runtime_b = tmp_path / "runtime-b"
    enforce_isolation(database_a, database_b, runtime_a, runtime_b, 8001, 8002)
    with pytest.raises(ValueError, match="database"):
        enforce_isolation(database_a, database_a, runtime_a, runtime_b, 8001, 8002)
    with pytest.raises(ValueError, match="runtime"):
        enforce_isolation(database_a, database_b, runtime_a, runtime_a, 8001, 8002)
    with pytest.raises(ValueError, match="ports"):
        enforce_isolation(database_a, database_b, runtime_a, runtime_b, 8001, 8001)


def test_three_way_result_equivalence():
    result = {
        "valid": True,
        "artifact_integrity_valid": True,
        "cryptographic_valid": True,
        "provider_trusted": True,
        "federation_state_valid": True,
        "transparency_verified": True,
        "witness_quorum_met": True,
        "checkpoint_gossip_consistent": True,
        "federation_conflict": False,
        "split_view_detected": False,
        "witness_equivocation_detected": False,
        "achieved_level": "full",
        "failure_code": None,
    }
    assert equivalent_results(result, dict(result), dict(result))
    changed = dict(result, witness_quorum_met=False)
    assert not equivalent_results(result, result, changed)


def test_cross_installation_report_path_redaction(tmp_path):
    redacted = redact_path(Path(tmp_path) / "instance-a.db", "database-a")
    assert redacted["label"] == "database-a"
    assert str(tmp_path) not in str(redacted)
    assert len(redacted["identity_sha256"]) == 64
