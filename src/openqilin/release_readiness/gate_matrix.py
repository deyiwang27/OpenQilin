"""Deterministic release gate command matrix for M4 hardening."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReleaseGateCategory(str, Enum):
    """Release-gate category labels."""

    STATIC = "static"
    TEST = "test"
    SMOKE = "smoke"
    CONFORMANCE = "conformance"


@dataclass(frozen=True, slots=True)
class ReleaseGateStep:
    """Single release-gate command contract."""

    step_id: str
    category: ReleaseGateCategory
    command: str
    success_criteria: str
    required_for_promotion: bool
    runs_in_ci: bool


def build_release_gate_matrix() -> tuple[ReleaseGateStep, ...]:
    """Return deterministic release-gate matrix used by CI and release ops."""

    return (
        ReleaseGateStep(
            step_id="lint_ruff_check",
            category=ReleaseGateCategory.STATIC,
            command="uv run ruff check .",
            success_criteria="exit code 0 and no lint violations",
            required_for_promotion=True,
            runs_in_ci=True,
        ),
        ReleaseGateStep(
            step_id="format_ruff_check",
            category=ReleaseGateCategory.STATIC,
            command="uv run ruff format --check .",
            success_criteria="exit code 0 and no format drift",
            required_for_promotion=True,
            runs_in_ci=True,
        ),
        ReleaseGateStep(
            step_id="type_mypy",
            category=ReleaseGateCategory.STATIC,
            command="uv run mypy .",
            success_criteria="exit code 0 and no type errors",
            required_for_promotion=True,
            runs_in_ci=True,
        ),
        ReleaseGateStep(
            step_id="spec_integrity",
            category=ReleaseGateCategory.STATIC,
            command="uv run python ops/scripts/check_spec_integrity.py",
            success_criteria="exit code 0 and no spec/doc drift violations",
            required_for_promotion=True,
            runs_in_ci=True,
        ),
        ReleaseGateStep(
            step_id="migration_rollback_readiness",
            category=ReleaseGateCategory.STATIC,
            command="uv run python ops/scripts/check_migration_rollback_readiness.py",
            success_criteria="exit code 0 and rollback-readiness policy checks pass",
            required_for_promotion=True,
            runs_in_ci=True,
        ),
        ReleaseGateStep(
            step_id="release_gate_matrix_integrity",
            category=ReleaseGateCategory.STATIC,
            command="uv run python ops/scripts/check_release_gate_matrix.py",
            success_criteria="exit code 0 and matrix/workflow/compose contracts align",
            required_for_promotion=True,
            runs_in_ci=True,
        ),
        ReleaseGateStep(
            step_id="pytest_unit",
            category=ReleaseGateCategory.TEST,
            command="uv run pytest tests/unit",
            success_criteria="all unit tests pass",
            required_for_promotion=True,
            runs_in_ci=True,
        ),
        ReleaseGateStep(
            step_id="pytest_component",
            category=ReleaseGateCategory.TEST,
            command="uv run pytest tests/component",
            success_criteria="all component tests pass (requires live OPA)",
            required_for_promotion=True,
            runs_in_ci=True,
        ),
        ReleaseGateStep(
            step_id="pytest_contract_integration",
            category=ReleaseGateCategory.TEST,
            command="uv run pytest tests/contract tests/integration",
            success_criteria="all contract/integration tests pass",
            required_for_promotion=True,
            runs_in_ci=True,
        ),
        ReleaseGateStep(
            step_id="pytest_conformance",
            category=ReleaseGateCategory.CONFORMANCE,
            command="uv run pytest tests/conformance",
            success_criteria="all conformance tests pass",
            required_for_promotion=True,
            runs_in_ci=True,
        ),
        ReleaseGateStep(
            step_id="full_profile_bootstrap_smoke",
            category=ReleaseGateCategory.SMOKE,
            command="docker compose --profile full run --rm admin bootstrap --smoke-in-process",
            success_criteria="admin bootstrap exits 0 under full profile with in-process smoke",
            required_for_promotion=True,
            runs_in_ci=False,
        ),
    )


def ci_gate_steps(matrix: tuple[ReleaseGateStep, ...] | None = None) -> tuple[ReleaseGateStep, ...]:
    """Return steps that must run in CI."""

    source = matrix or build_release_gate_matrix()
    return tuple(step for step in source if step.runs_in_ci)


def release_candidate_gate_steps(
    matrix: tuple[ReleaseGateStep, ...] | None = None,
) -> tuple[ReleaseGateStep, ...]:
    """Return promotion-blocking steps for release-candidate validation."""

    source = matrix or build_release_gate_matrix()
    return tuple(step for step in source if step.required_for_promotion)


def validate_release_gate_matrix(
    matrix: tuple[ReleaseGateStep, ...] | None = None,
) -> list[str]:
    """Validate release gate matrix invariants."""

    source = matrix or build_release_gate_matrix()
    failures: list[str] = []

    if not source:
        return ["release gate matrix must not be empty"]

    step_ids = [step.step_id for step in source]
    duplicate_ids = sorted({step_id for step_id in step_ids if step_ids.count(step_id) > 1})
    if duplicate_ids:
        failures.append(f"duplicate step_id values: {', '.join(duplicate_ids)}")

    required_steps = [step for step in source if step.required_for_promotion]
    if not required_steps:
        failures.append("matrix must contain required_for_promotion steps")

    if not any(step.category is ReleaseGateCategory.SMOKE for step in required_steps):
        failures.append("matrix must contain at least one promotion-required smoke step")
    if not any(step.category is ReleaseGateCategory.CONFORMANCE for step in required_steps):
        failures.append("matrix must contain at least one promotion-required conformance step")

    ci_steps = [step for step in source if step.runs_in_ci]
    if not ci_steps:
        failures.append("matrix must contain CI steps")
    if not any(step.category is ReleaseGateCategory.CONFORMANCE for step in ci_steps):
        failures.append("CI steps must include at least one conformance gate")

    for step in source:
        if not step.step_id.strip():
            failures.append("step_id must be non-empty")
        if not step.command.strip():
            failures.append(f"{step.step_id}: command must be non-empty")
        if not step.success_criteria.strip():
            failures.append(f"{step.step_id}: success_criteria must be non-empty")

    return failures
