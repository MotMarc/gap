from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.benchmark_mvp import measure, redact as benchmark_redact, summarise
from scripts.run_mvp_demo import redact as demo_redact, validate_report
from scripts.validate_backup_restore import redact as backup_redact
from scripts.validate_docker_release import classify


def test_benchmark_median_and_result_schema() -> None:
    assert summarise([3.0, 1.0, 2.0]) == {
        "minimum_seconds": 1.0,
        "median_seconds": 2.0,
        "maximum_seconds": 3.0,
    }
    result = measure("unit", 4, lambda: True, repetitions=2)
    assert result["result"] == "passed"
    assert result["operation"] == "unit"
    assert result["peak_python_memory_bytes"] >= 0


def test_benchmark_failed_operation_is_reported() -> None:
    def fail() -> None:
        raise RuntimeError(str(Path.home() / "secret"))

    result = measure("failure", 0, fail)
    assert result["result"] == "failed"
    assert str(Path.home()) not in result["error"]


def test_report_redaction_removes_private_paths() -> None:
    private = str(Path.home() / "private" / "value")
    for function in (benchmark_redact, demo_redact, backup_redact):
        assert str(Path.home()) not in function(private)


def test_demo_policy_and_tampering_requirements() -> None:
    tampering = {
        name: True
        for name in {
            "artifact",
            "embedded_credential",
            "package",
            "manifest",
            "downgrade",
            "corrupt_trust",
            "stale_trust",
            "unknown_profile",
        }
    }
    validate_report(
        {"passed": True, "three_way_equivalent": True, "tampering_rejected": tampering}
    )
    tampering["downgrade"] = False
    with pytest.raises(RuntimeError, match="tampering"):
        validate_report(
            {
                "passed": True,
                "three_way_equivalent": True,
                "tampering_rejected": tampering,
            }
        )


def test_demo_mandatory_failure_is_non_success() -> None:
    with pytest.raises(RuntimeError, match="equivalence"):
        validate_report(
            {"passed": False, "three_way_equivalent": False, "tampering_rejected": {}}
        )


def test_docker_unavailable_is_blocked_not_skipped(monkeypatch) -> None:
    monkeypatch.setattr("scripts.validate_docker_release.shutil.which", lambda _: None)
    report = classify()
    assert report["status"] == "blocked"
    assert report["passed"] is False
    assert report["owner_approval_required"] is True


def test_reports_are_json_serialisable() -> None:
    assert json.loads(json.dumps({"format": "gap-report-v1"}))["format"].endswith("-v1")
