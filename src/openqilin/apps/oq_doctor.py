"""Standalone CLI entrypoint for the OpenQilin system doctor.

Usage:
    python -m openqilin.apps.oq_doctor               # direct
    docker compose --profile doctor run oq_doctor    # via compose

Exit codes:
    0 — all blocking checks passed (warnings allowed)
    1 — one or more blocking checks failed
"""

from __future__ import annotations

import sys

from openqilin.shared_kernel.doctor import DoctorReport, SystemDoctor
from openqilin.shared_kernel.settings import get_settings

_STATUS_ICON = {"pass": "✓", "warn": "!", "fail": "✗"}
_COL_WIDTH = 24


def main() -> None:
    """Run the doctor and print a tabular report."""
    settings = get_settings()
    doctor = SystemDoctor(settings=settings)
    report = doctor.run()
    _print_report(report)
    sys.exit(1 if report.has_failures() else 0)


def _print_report(report: DoctorReport) -> None:
    print(f"\n{'Check':<{_COL_WIDTH}} {'Status':<8} Detail")
    print("-" * 72)
    for check in report.checks:
        icon = _STATUS_ICON.get(check.status, "?")
        print(f"{check.name:<{_COL_WIDTH}} [{icon}] {check.status:<5}  {check.detail}")
    print()
    if report.all_passed():
        print("All checks passed. System is ready.")
    elif report.has_failures():
        print("One or more blocking checks FAILED. System cannot start.")
    else:
        print("Checks passed with warnings. Review items marked [!].")
    print()


if __name__ == "__main__":
    main()
