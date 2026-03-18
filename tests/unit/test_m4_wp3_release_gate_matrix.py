from openqilin.release_readiness.gate_matrix import (
    ReleaseGateCategory,
    build_release_gate_matrix,
    ci_gate_steps,
    release_candidate_gate_steps,
    validate_release_gate_matrix,
)


def test_release_gate_matrix_has_deterministic_step_ids() -> None:
    matrix = build_release_gate_matrix()

    assert [step.step_id for step in matrix] == [
        "lint_ruff_check",
        "format_ruff_check",
        "type_mypy",
        "spec_integrity",
        "migration_rollback_readiness",
        "release_gate_matrix_integrity",
        "pytest_unit",
        "pytest_component",
        "pytest_contract_integration",
        "pytest_conformance",
        "full_profile_bootstrap_smoke",
    ]


def test_release_gate_matrix_validation_passes() -> None:
    assert validate_release_gate_matrix() == []


def test_ci_gate_steps_exclude_docker_smoke_step() -> None:
    ci_steps = ci_gate_steps()

    assert all(step.runs_in_ci for step in ci_steps)
    assert all(
        step.category is not ReleaseGateCategory.SMOKE or "docker compose" not in step.command
        for step in ci_steps
    )


def test_release_candidate_steps_include_smoke_and_conformance() -> None:
    steps = release_candidate_gate_steps()
    categories = {step.category for step in steps}

    assert ReleaseGateCategory.SMOKE in categories
    assert ReleaseGateCategory.CONFORMANCE in categories
