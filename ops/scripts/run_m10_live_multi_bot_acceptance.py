"""Preflight and evidence-manifest initializer for M10 live multi-bot acceptance."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    name: str
    success: bool
    details: str


DEFAULT_MANIFEST_OUTPUT: Final[Path] = Path(
    "implementation/v1/planning/artifacts/m10_live_scenarios_manifest_latest.json"
)
DEFAULT_PREFLIGHT_OUTPUT: Final[Path] = Path(
    "implementation/v1/planning/artifacts/m10_live_preflight_latest.json"
)
DEFAULT_NOTES_OUTPUT: Final[Path] = Path(
    "implementation/v1/planning/artifacts/m10_live_acceptance_notes.md"
)


def _check_command(name: str) -> PreflightCheck:
    resolved = shutil.which(name)
    return PreflightCheck(
        name=f"command_{name}",
        success=resolved is not None,
        details=resolved or "not found",
    )


def _check_env(name: str) -> PreflightCheck:
    value = os.getenv(name)
    return PreflightCheck(
        name=f"env_{name}",
        success=bool(value and value.strip()),
        details="set" if bool(value and value.strip()) else "missing",
    )


def _check_any_env(name: str, *candidates: str) -> PreflightCheck:
    for candidate in candidates:
        value = os.getenv(candidate)
        if value and value.strip():
            return PreflightCheck(
                name=name,
                success=True,
                details=f"{candidate}=set",
            )
    return PreflightCheck(
        name=name,
        success=False,
        details="missing",
    )


def _build_preflight_results() -> tuple[PreflightCheck, ...]:
    return (
        _check_command("docker"),
        _check_env("OPENQILIN_DISCORD_MULTI_BOT_ENABLED"),
        _check_any_env(
            "env_OPENQILIN_DISCORD_ROLE_BOT_TOKENS_FILE_OR_JSON",
            "OPENQILIN_DISCORD_ROLE_BOT_TOKENS_FILE",
            "OPENQILIN_DISCORD_ROLE_BOT_TOKENS_JSON",
        ),
        _check_env("OPENQILIN_DISCORD_REQUIRED_ROLE_BOTS_CSV"),
        _check_env("OPENQILIN_GEMINI_API_KEY"),
        _check_env("OPENQILIN_CONNECTOR_SHARED_SECRET"),
    )


def _print_results(results: tuple[PreflightCheck, ...]) -> bool:
    has_failure = False
    for result in results:
        status = "OK" if result.success else "FAIL"
        print(f"[{status}] {result.name}: {result.details}")
        if not result.success:
            has_failure = True
    return not has_failure


def _write_preflight_report(
    *,
    output_path: Path,
    results: tuple[PreflightCheck, ...],
    preflight_ok: bool,
) -> Path:
    payload: dict[str, Any] = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "preflight_ok": preflight_ok,
        "checks": [
            {
                "name": result.name,
                "success": result.success,
                "details": result.details,
            }
            for result in results
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def _write_manifest(*, output_path: Path, project_id: str) -> Path:
    payload = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "project_id": project_id,
        "status": "pending_manual_execution",
        "scenarios": [
            {"name": "role_dm_matrix"},
            {"name": "mention_group_chat"},
            {"name": "long_response_chunking"},
            {"name": "tool_read_write_governance"},
        ],
        "required_artifacts": [
            "discord_screenshots",
            "docker_compose_ps_output",
            "api_app_logs",
            "discord_bot_worker_logs",
            "trace_and_task_correlation_notes",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def _write_notes_template(*, output_path: Path, project_id: str) -> Path:
    template = (
        "# M10 Live Acceptance Notes\n\n"
        f"- project_id: `{project_id}`\n"
        "- execution_date_utc: `<fill>`\n"
        "- operator: `<fill>`\n\n"
        "## Execution Summary\n"
        "- overall_result: `<pass|fail>`\n"
        "- blockers_or_anomalies: `<fill>`\n\n"
        "## Scenario Evidence\n"
        "### role_dm_matrix\n"
        "- evidence_links: `<discord screenshots / trace ids / log excerpts>`\n\n"
        "### mention_group_chat\n"
        "- evidence_links: `<discord screenshots / trace ids / log excerpts>`\n\n"
        "### long_response_chunking\n"
        "- evidence_links: `<discord screenshots / trace ids / log excerpts>`\n\n"
        "### tool_read_write_governance\n"
        "- evidence_links: `<discord screenshots / trace ids / log excerpts>`\n\n"
        "## Command Outputs\n"
        "- docker_compose_ps: `<paste/link>`\n"
        "- api_app_logs: `<paste/link>`\n"
        "- discord_bot_worker_logs: `<paste/link>`\n\n"
        "## Trace Correlation\n"
        "- task_trace_mapping: `<task_id -> trace_id -> discord message evidence>`\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template, encoding="utf-8")
    return output_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run M10 live multi-bot acceptance preflight and initialize evidence files.",
    )
    parser.add_argument(
        "--mode",
        choices=("preflight", "init-manifest", "init-notes"),
        default="preflight",
        help="Execution mode.",
    )
    parser.add_argument(
        "--project-id",
        default="project_m10_live",
        help="Project id label recorded in evidence manifest.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_MANIFEST_OUTPUT,
        help="Path to scenario manifest output JSON.",
    )
    parser.add_argument(
        "--preflight-report",
        type=Path,
        default=DEFAULT_PREFLIGHT_OUTPUT,
        help="Path to write deterministic preflight report JSON.",
    )
    parser.add_argument(
        "--notes-output",
        type=Path,
        default=DEFAULT_NOTES_OUTPUT,
        help="Path to write notes template markdown for live acceptance.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    results = _build_preflight_results()
    preflight_ok = _print_results(results)
    preflight_report_path = _write_preflight_report(
        output_path=args.preflight_report,
        results=results,
        preflight_ok=preflight_ok,
    )
    print(f"[INFO] preflight_report: {preflight_report_path}")
    if not preflight_ok:
        print("[ERROR] M10 live acceptance preflight failed.")
        return 1
    if args.mode == "preflight":
        print("[INFO] M10 live acceptance preflight passed.")
        return 0
    if args.mode == "init-notes":
        notes_output = _write_notes_template(
            output_path=args.notes_output,
            project_id=args.project_id,
        )
        print(f"[INFO] notes_template_initialized: {notes_output}")
        return 0
    manifest_output = _write_manifest(output_path=args.output, project_id=args.project_id)
    print(f"[INFO] manifest_initialized: {manifest_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
