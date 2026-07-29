from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Callable

from pydantic import BaseModel, ConfigDict

from .serialization import canonical_json
from .version import __version__


class ConformanceCase(BaseModel):
    case_id: str
    required: bool = True
    status: str
    detail: str | None = None
    model_config = ConfigDict(extra="forbid")


class ConformanceReport(BaseModel):
    report_format: str = "gap-conformance-report-v1"
    suite: str
    application_version: str = __version__
    generated_at: datetime
    passed: bool
    cases: list[ConformanceCase]
    report_digest: str


def create_report(
    suite: str,
    cases: list[ConformanceCase | dict],
    *,
    generated_at: datetime | None = None,
) -> ConformanceReport:
    normalized = sorted(
        (ConformanceCase.model_validate(item) for item in cases),
        key=lambda item: item.case_id,
    )
    passed = all(
        case.status == "passed" or (case.status == "skipped" and not case.required)
        for case in normalized
    )
    payload = {
        "report_format": "gap-conformance-report-v1",
        "suite": suite,
        "application_version": __version__,
        "generated_at": (generated_at or datetime.now(timezone.utc))
        .isoformat()
        .replace("+00:00", "Z"),
        "passed": passed,
        "cases": [
            case.model_dump(mode="json", exclude_none=True) for case in normalized
        ],
    }
    return ConformanceReport(
        **payload, report_digest=hashlib.sha256(canonical_json(payload)).hexdigest()
    )


def verify_report(report: ConformanceReport | dict) -> bool:
    report = ConformanceReport.model_validate(report)
    payload = report.model_dump(
        mode="json", exclude={"report_digest"}, exclude_none=True
    )
    return hashlib.sha256(canonical_json(payload)).hexdigest() == report.report_digest


def run_cases(suite: str, cases: dict[str, Callable[[], None]]) -> ConformanceReport:
    results = []
    for case_id, callback in sorted(cases.items()):
        try:
            callback()
            results.append(ConformanceCase(case_id=case_id, status="passed"))
        except Exception:
            results.append(
                ConformanceCase(
                    case_id=case_id,
                    status="failed",
                    detail="The conformance assertion failed.",
                )
            )
    return create_report(suite, results)
