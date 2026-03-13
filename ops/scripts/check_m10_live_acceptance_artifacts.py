"""Static checks for M10 live acceptance artifact completeness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate deterministic M10 live acceptance artifact set.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = args.repo_root.resolve()
    failures: list[str] = []

    preflight_report = (
        repo_root / "implementation/v1/planning/artifacts/m10_live_preflight_latest.json"
    )
    manifest = (
        repo_root / "implementation/v1/planning/artifacts/m10_live_scenarios_manifest_latest.json"
    )
    notes = repo_root / "implementation/v1/planning/artifacts/m10_live_acceptance_notes.md"

    for artifact in (preflight_report, manifest, notes):
        if not artifact.exists():
            failures.append(f"missing required M10 artifact: {artifact.relative_to(repo_root)}")

    if preflight_report.exists():
        payload = _load_json(preflight_report)
        if not isinstance(payload.get("checks"), list):
            failures.append("preflight report missing checks[] list")
        if "generated_at" not in payload:
            failures.append("preflight report missing generated_at")
        if payload.get("preflight_ok") is not True:
            failures.append(
                "preflight report indicates failure (preflight_ok != true); "
                "live execution prerequisites are not satisfied"
            )

    if manifest.exists():
        payload = _load_json(manifest)
        if payload.get("status") != "pending_manual_execution":
            failures.append(
                "manifest status must be 'pending_manual_execution' before live execution"
            )
        scenario_names = {
            scenario.get("name")
            for scenario in payload.get("scenarios", [])
            if isinstance(scenario, dict)
        }
        required_scenarios = {
            "role_dm_matrix",
            "mention_group_chat",
            "long_response_chunking",
            "tool_read_write_governance",
        }
        if scenario_names != required_scenarios:
            failures.append("manifest scenarios mismatch for M10 live acceptance")
        required_artifacts = set(payload.get("required_artifacts", []))
        for key in (
            "discord_screenshots",
            "docker_compose_ps_output",
            "api_app_logs",
            "discord_bot_worker_logs",
            "trace_and_task_correlation_notes",
        ):
            if key not in required_artifacts:
                failures.append(f"manifest missing required_artifacts entry: {key}")

    if notes.exists():
        text = _load_text(notes)
        for snippet in (
            "## Execution Summary",
            "## Scenario Evidence",
            "### role_dm_matrix",
            "### mention_group_chat",
            "### long_response_chunking",
            "### tool_read_write_governance",
            "## Command Outputs",
            "## Trace Correlation",
        ):
            if snippet not in text:
                failures.append(f"notes template missing required section: {snippet!r}")

    if failures:
        print("M10 live acceptance artifact checks failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("M10 live acceptance artifact checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
