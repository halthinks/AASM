from __future__ import annotations

import sys
from pathlib import Path

import pytest


def _escape(value: str) -> str:
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
    )


class GitHubAnnotationPlugin:
    """Emit useful GitHub annotations while preserving pytest as the authority."""

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if not report.failed:
            return
        path, line, _ = report.location
        try:
            line_number = int(line) + 1
        except Exception:
            line_number = 1
        detail = str(report.longrepr)
        summary = detail.splitlines()[-1] if detail else f"{report.nodeid} failed during {report.when}"
        print(
            f"::error file={_escape(str(Path(path)))},line={line_number}::"
            f"{_escape(report.nodeid)} — {_escape(summary)}",
            file=sys.stderr,
            flush=True,
        )

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if not report.failed:
            return
        detail = str(report.longrepr)
        summary = detail.splitlines()[-1] if detail else f"collection failed: {report.nodeid}"
        print(
            f"::error::{_escape(report.nodeid)} — {_escape(summary)}",
            file=sys.stderr,
            flush=True,
        )


def main() -> int:
    args = sys.argv[1:] or ["-q"]
    return int(pytest.main(args, plugins=[GitHubAnnotationPlugin()]))


if __name__ == "__main__":
    raise SystemExit(main())
