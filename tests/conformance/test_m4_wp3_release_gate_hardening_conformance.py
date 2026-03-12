from pathlib import Path

from openqilin.release_readiness.gate_matrix import ci_gate_steps, release_candidate_gate_steps


def test_m4_wp3_conformance_ci_workflow_matches_ci_gate_matrix() -> None:
    project_root = Path(__file__).resolve().parents[2]
    workflow = (project_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    for step in ci_gate_steps():
        assert step.command in workflow


def test_m4_wp3_conformance_compose_full_profile_admin_smoke_contract() -> None:
    project_root = Path(__file__).resolve().parents[2]
    compose_text = (project_root / "compose.yml").read_text(encoding="utf-8")

    assert 'profiles: ["full"]' in compose_text
    assert 'command: ["bootstrap", "--smoke-in-process"]' in compose_text


def test_m4_wp3_conformance_release_candidate_matrix_contains_smoke_and_conformance() -> None:
    steps = release_candidate_gate_steps()
    commands = {step.command for step in steps}

    assert "docker compose --profile full run --rm admin bootstrap --smoke-in-process" in commands
    assert "uv run pytest tests/conformance" in commands
