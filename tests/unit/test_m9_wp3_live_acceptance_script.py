from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path


def _load_script_main():
    module_path = (
        Path(__file__).resolve().parents[2] / "ops/scripts/run_m9_live_discord_acceptance.py"
    )
    spec = importlib.util.spec_from_file_location("m9_live_acceptance_script", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.main


def test_m9_wp3_live_acceptance_script_preflight_fails_without_required_prereqs(
    tmp_path: Path, monkeypatch
) -> None:
    main = _load_script_main()
    monkeypatch.setenv("OPENQILIN_DISCORD_BOT_TOKEN", "")
    monkeypatch.setenv("OPENQILIN_GEMINI_API_KEY", "")
    monkeypatch.setenv("OPENQILIN_CONNECTOR_SHARED_SECRET", "")
    monkeypatch.setattr("shutil.which", lambda _: None)
    preflight_report = tmp_path / "preflight.json"

    code = main(["--mode", "preflight", "--preflight-report", str(preflight_report)])

    assert code == 1
    payload = json.loads(preflight_report.read_text(encoding="utf-8"))
    assert payload["preflight_ok"] is False
    assert len(payload["checks"]) == 4


def test_m9_wp3_live_acceptance_script_initializes_manifest_when_preflight_passes(
    tmp_path: Path, monkeypatch
) -> None:
    main = _load_script_main()
    monkeypatch.setenv("OPENQILIN_DISCORD_BOT_TOKEN", "token")
    monkeypatch.setenv("OPENQILIN_GEMINI_API_KEY", "gemini")
    monkeypatch.setenv("OPENQILIN_CONNECTOR_SHARED_SECRET", "secret")
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/docker")
    output = tmp_path / "manifest.json"
    preflight_report = tmp_path / "preflight.json"

    code = main(
        [
            "--mode",
            "init-manifest",
            "--project-id",
            "project_live_001",
            "--output",
            str(output),
            "--preflight-report",
            str(preflight_report),
        ]
    )

    assert code == 0
    preflight_payload = json.loads(preflight_report.read_text(encoding="utf-8"))
    assert preflight_payload["preflight_ok"] is True
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["project_id"] == "project_live_001"
    assert payload["status"] == "pending_manual_execution"


def test_m9_wp3_live_acceptance_script_initializes_notes_template_when_preflight_passes(
    tmp_path: Path, monkeypatch
) -> None:
    main = _load_script_main()
    monkeypatch.setenv("OPENQILIN_DISCORD_BOT_TOKEN", "token")
    monkeypatch.setenv("OPENQILIN_GEMINI_API_KEY", "gemini")
    monkeypatch.setenv("OPENQILIN_CONNECTOR_SHARED_SECRET", "secret")
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/docker")
    notes_output = tmp_path / "notes.md"
    preflight_report = tmp_path / "preflight.json"

    code = main(
        [
            "--mode",
            "init-notes",
            "--project-id",
            "project_live_002",
            "--notes-output",
            str(notes_output),
            "--preflight-report",
            str(preflight_report),
        ]
    )

    assert code == 0
    notes_text = notes_output.read_text(encoding="utf-8")
    assert "project_live_002" in notes_text
    assert "## Execution Summary" in notes_text
