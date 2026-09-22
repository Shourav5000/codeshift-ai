from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def _relative_path(
    raw_path: str | None,
    repo_path: Path,
) -> str | None:
    if not raw_path:
        return None

    try:
        return str(
            Path(raw_path)
            .resolve()
            .relative_to(
                repo_path.resolve()
            )
        )
    except Exception:
        return raw_path


def _as_list(
    value,
) -> list:
    if value is None:
        return []

    if isinstance(
        value,
        list,
    ):
        return value

    return [value]


def _normalize_finding(
    finding: dict,
    repo_path: Path,
) -> dict:

    extra = finding.get(
        "extra",
        {},
    )

    metadata = extra.get(
        "metadata",
        {},
    )

    start = finding.get(
        "start",
        {},
    )

    end = finding.get(
        "end",
        {},
    )

    severity = (
        extra.get(
            "severity"
        )
        or metadata.get(
            "severity"
        )
        or "UNKNOWN"
    )

    category = metadata.get(
        "category"
    )

    confidence = metadata.get(
        "confidence"
    )

    impact = metadata.get(
        "impact"
    )

    likelihood = metadata.get(
        "likelihood"
    )

    return {
        "rule_id": finding.get(
            "check_id"
        ),

        "severity": severity,

        "category": category,

        "path": _relative_path(
            finding.get(
                "path"
            ),
            repo_path,
        ),

        "start_line": start.get(
            "line"
        ),

        "start_column": start.get(
            "col"
        ),

        "end_line": end.get(
            "line"
        ),

        "end_column": end.get(
            "col"
        ),

        "message": extra.get(
            "message"
        ),

        "confidence": confidence,

        "impact": impact,

        "likelihood": likelihood,

        "cwe": _as_list(
            metadata.get(
                "cwe"
            )
        ),

        "owasp": _as_list(
            metadata.get(
                "owasp"
            )
        ),

        "technology": _as_list(
            metadata.get(
                "technology"
            )
        ),

        "references": _as_list(
            metadata.get(
                "references"
            )
        ),

        "vulnerability_class": _as_list(
            metadata.get(
                "vulnerability_class"
            )
        ),

        "source": metadata.get(
            "source"
        ),

        "shortlink": metadata.get(
            "shortlink"
        ),
    }


def _build_severity_counts(
    findings: list[dict],
) -> dict:

    counts = {
        "ERROR": 0,
        "WARNING": 0,
        "INFO": 0,
        "UNKNOWN": 0,
    }

    for finding in findings:
        severity = str(
            finding.get(
                "severity",
                "UNKNOWN",
            )
        ).upper()

        if severity not in counts:
            severity = "UNKNOWN"

        counts[severity] += 1

    return counts


def _build_category_counts(
    findings: list[dict],
) -> dict:

    counts: dict[str, int] = {}

    for finding in findings:
        category = (
            finding.get(
                "category"
            )
            or "unknown"
        )

        counts[category] = (
            counts.get(
                category,
                0,
            )
            + 1
        )

    return counts


def _normalize_errors(
    errors,
) -> list[dict]:

    if not isinstance(
        errors,
        list,
    ):
        return []

    normalized = []

    for error in errors:
        if not isinstance(
            error,
            dict,
        ):
            normalized.append(
                {
                    "message": str(
                        error
                    )
                }
            )
            continue

        normalized.append(
            {
                "type": error.get(
                    "type"
                ),
                "level": error.get(
                    "level"
                ),
                "message": error.get(
                    "message"
                ),
                "path": error.get(
                    "path"
                ),
            }
        )

    return normalized


def _get_semgrep_command() -> list[str] | None:

    semgrep_path = shutil.which(
        "semgrep"
    )

    if semgrep_path:
        return [
            semgrep_path
        ]

    uvx_path = shutil.which(
        "uvx"
    )

    if uvx_path:
        return [
            uvx_path,
            "semgrep",
        ]

    return None


def scan_with_semgrep(
    repo_path: Path,
) -> dict:

    repo_path = Path(
        repo_path
    )

    semgrep_command = (
        _get_semgrep_command()
    )

    if not semgrep_command:
        return {
            "provider": "Semgrep",
            "status": "unavailable",
            "finding_count": 0,
            "error_count": 1,
            "severity_counts": {},
            "category_counts": {},
            "findings": [],
            "scan_errors": [
                {
                    "message": (
                        "Semgrep executable "
                        "was not found."
                    )
                }
            ],
        }

    command = [
        *semgrep_command,
        "scan",
        "--config=auto",
        "--json",
        "--quiet",
        str(
            repo_path
        ),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
        )

    except subprocess.TimeoutExpired:
        return {
            "provider": "Semgrep",
            "status": "timeout",
            "finding_count": 0,
            "error_count": 1,
            "severity_counts": {},
            "category_counts": {},
            "findings": [],
            "scan_errors": [
                {
                    "message": (
                        "Semgrep scan timed out."
                    )
                }
            ],
        }

    except OSError as exc:
        return {
            "provider": "Semgrep",
            "status": "error",
            "finding_count": 0,
            "error_count": 1,
            "severity_counts": {},
            "category_counts": {},
            "findings": [],
            "scan_errors": [
                {
                    "message": str(
                        exc
                    )
                }
            ],
        }

    stdout = (
        result.stdout.strip()
    )

    if not stdout:
        return {
            "provider": "Semgrep",
            "status": "error",
            "exit_code": (
                result.returncode
            ),
            "finding_count": 0,
            "error_count": 1,
            "severity_counts": {},
            "category_counts": {},
            "findings": [],
            "scan_errors": [
                {
                    "message": (
                        result.stderr.strip()
                        or (
                            "Semgrep returned "
                            "no JSON output."
                        )
                    )
                }
            ],
        }

    try:
        payload = json.loads(
            stdout
        )

    except json.JSONDecodeError as exc:
        return {
            "provider": "Semgrep",
            "status": "error",
            "exit_code": (
                result.returncode
            ),
            "finding_count": 0,
            "error_count": 1,
            "severity_counts": {},
            "category_counts": {},
            "findings": [],
            "scan_errors": [
                {
                    "message": (
                        "Invalid Semgrep "
                        f"JSON output: {exc}"
                    )
                }
            ],
        }

    raw_findings = payload.get(
        "results",
        [],
    )

    if not isinstance(
        raw_findings,
        list,
    ):
        raw_findings = []

    findings = [
        _normalize_finding(
            finding,
            repo_path,
        )
        for finding in raw_findings
        if isinstance(
            finding,
            dict,
        )
    ]

    scan_errors = (
        _normalize_errors(
            payload.get(
                "errors",
                [],
            )
        )
    )

    return {
        "provider": "Semgrep",

        "status": "completed",

        "exit_code": (
            result.returncode
        ),

        "finding_count": (
            len(
                findings
            )
        ),

        "error_count": (
            len(
                scan_errors
            )
        ),

        "severity_counts": (
            _build_severity_counts(
                findings
            )
        ),

        "category_counts": (
            _build_category_counts(
                findings
            )
        ),

        "findings": findings,

        "scan_errors": (
            scan_errors
        ),
    }