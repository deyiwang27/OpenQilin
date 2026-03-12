from pathlib import Path
import re

from openqilin.release_readiness.gate_matrix import ci_gate_steps, release_candidate_gate_steps


def _extract_run_commands(ci_workflow_text: str) -> set[str]:
    pattern = re.compile(r"^\s*run:\s*(?P<command>\S.+?)\s*$", re.MULTILINE)
    return {match.group("command").strip() for match in pattern.finditer(ci_workflow_text)}


def _extract_compose_service_block(compose_text: str, service_name: str) -> str | None:
    pattern = re.compile(
        rf"(?ms)^  {re.escape(service_name)}:\n(?P<body>(?:    .*\n)+?)(?=^  [a-zA-Z0-9_]+:|\Z)"
    )
    match = pattern.search(compose_text)
    if match is None:
        return None
    return match.group("body")


def test_m4_wp3_conformance_ci_workflow_matches_ci_gate_matrix() -> None:
    project_root = Path(__file__).resolve().parents[2]
    workflow = (project_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    run_commands = _extract_run_commands(workflow)

    for step in ci_gate_steps():
        assert step.command in run_commands


def test_m4_wp3_conformance_compose_full_profile_admin_smoke_contract() -> None:
    project_root = Path(__file__).resolve().parents[2]
    compose_text = (project_root / "compose.yml").read_text(encoding="utf-8")
    admin_block = _extract_compose_service_block(compose_text, "admin")

    assert admin_block is not None
    assert 'profiles: ["full"]' in admin_block
    assert 'command: ["bootstrap", "--smoke-in-process"]' in admin_block


def test_m4_wp3_conformance_release_candidate_matrix_contains_smoke_and_conformance() -> None:
    steps = release_candidate_gate_steps()
    commands = {step.command for step in steps}

    assert "docker compose --profile full run --rm admin bootstrap --smoke-in-process" in commands
    assert "uv run pytest tests/conformance" in commands
