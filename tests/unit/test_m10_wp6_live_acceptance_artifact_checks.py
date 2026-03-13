from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_script_main():
    module_path = (
        Path(__file__).resolve().parents[2] / "ops/scripts/check_m10_live_acceptance_artifacts.py"
    )
    spec = importlib.util.spec_from_file_location("m10_live_artifact_checks_script", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.main


def _write_valid_artifact_set(repo_root: Path) -> None:
    artifact_dir = repo_root / "implementation/v1/planning/artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    (artifact_dir / "m10_live_preflight_latest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-03-13T00:00:00+00:00",
                "preflight_ok": True,
                "checks": [],
            }
        ),
        encoding="utf-8",
    )
    (artifact_dir / "m10_live_scenarios_manifest_latest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-03-13T00:00:00+00:00",
                "project_id": "project_live_001",
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
        ),
        encoding="utf-8",
    )
    (artifact_dir / "m10_live_acceptance_notes.md").write_text(
        "\n".join(
            (
                "## Execution Summary",
                "## Scenario Evidence",
                "### role_dm_matrix",
                "### mention_group_chat",
                "### long_response_chunking",
                "### tool_read_write_governance",
                "## Command Outputs",
                "## Trace Correlation",
            )
        ),
        encoding="utf-8",
    )


def test_m10_wp6_artifact_check_script_passes_with_valid_artifacts(tmp_path: Path) -> None:
    main = _load_script_main()
    _write_valid_artifact_set(tmp_path)

    code = main(["--repo-root", str(tmp_path)])

    assert code == 0


def test_m10_wp6_artifact_check_script_fails_when_preflight_not_ready(tmp_path: Path) -> None:
    main = _load_script_main()
    _write_valid_artifact_set(tmp_path)
    preflight = tmp_path / "implementation/v1/planning/artifacts/m10_live_preflight_latest.json"
    preflight.write_text(
        json.dumps(
            {
                "generated_at": "2026-03-13T00:00:00+00:00",
                "preflight_ok": False,
                "checks": [],
            }
        ),
        encoding="utf-8",
    )

    code = main(["--repo-root", str(tmp_path)])

    assert code == 1
