from __future__ import annotations

from pathlib import Path

from openqilin.data_access.repositories.artifacts import InMemoryProjectArtifactRepository
from openqilin.data_access.repositories.governance import InMemoryGovernanceRepository


def _seed_approved_project(repository: InMemoryGovernanceRepository) -> None:
    repository.create_project(
        project_id="project_m6_wp1",
        name="M6 Artifact Persistence",
        objective="Seed objective",
    )
    repository.transition_project_status(
        project_id="project_m6_wp1",
        next_status="approved",
        reason_code="triad_approval",
        actor_role="ceo",
        trace_id="trace-m6-wp1-approve",
    )


def test_initialize_project_persists_activation_baseline_artifacts(
    tmp_path: Path,
) -> None:
    artifact_repository = InMemoryProjectArtifactRepository(system_root=tmp_path / "system_root")
    repository = InMemoryGovernanceRepository(artifact_repository=artifact_repository)
    _seed_approved_project(repository)

    project = repository.initialize_project(
        project_id="project_m6_wp1",
        objective="Deliver governed project documentation persistence",
        budget_currency_total=120.0,
        budget_quota_total=5000.0,
        metric_plan={"delivery": "mvp_acceptance_pass"},
        workforce_plan={"project_manager": "1", "specialist": "2"},
        actor_id="cwo_1",
        actor_role="cwo",
        trace_id="trace-m6-wp1-init",
    )

    initialization = project.initialization
    assert initialization is not None
    assert initialization.charter_storage_uri is not None
    assert initialization.charter_content_hash is not None
    assert initialization.scope_statement_storage_uri is not None
    assert initialization.scope_statement_content_hash is not None
    assert initialization.budget_plan_storage_uri is not None
    assert initialization.budget_plan_content_hash is not None
    assert initialization.metric_plan_storage_uri is not None
    assert initialization.metric_plan_content_hash is not None
    assert initialization.workforce_plan_storage_uri is not None
    assert initialization.workforce_plan_content_hash is not None
    assert initialization.execution_plan_storage_uri is not None
    assert initialization.execution_plan_content_hash is not None
    assert initialization.charter_storage_uri.startswith(
        str((tmp_path / "system_root" / "projects" / "project_m6_wp1").resolve())
    )
    assert artifact_repository.verify_pointer_hash(
        project_id="project_m6_wp1",
        artifact_type="project_charter",
    )
    assert artifact_repository.verify_pointer_hash(
        project_id="project_m6_wp1",
        artifact_type="scope_statement",
    )
    assert artifact_repository.verify_pointer_hash(
        project_id="project_m6_wp1",
        artifact_type="budget_plan",
    )
    assert artifact_repository.verify_pointer_hash(
        project_id="project_m6_wp1",
        artifact_type="success_metrics",
    )
    assert artifact_repository.verify_pointer_hash(
        project_id="project_m6_wp1",
        artifact_type="workforce_plan",
    )
    assert artifact_repository.verify_pointer_hash(
        project_id="project_m6_wp1",
        artifact_type="execution_plan",
    )
