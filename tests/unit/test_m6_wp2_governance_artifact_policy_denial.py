from __future__ import annotations

from pathlib import Path

import pytest

from openqilin.data_access.repositories.artifacts import ProjectDocumentPolicy
from openqilin.data_access.repositories.governance import GovernanceRepositoryError
from tests.testing.infra_stubs import (
    InMemoryGovernanceRepository,
    InMemoryProjectArtifactRepository,
)


def _seed_approved_project(repository: InMemoryGovernanceRepository) -> None:
    repository.create_project(
        project_id="project_m6_wp2",
        name="M6 Policy Denial",
        objective="Seed objective",
    )
    repository.transition_project_status(
        project_id="project_m6_wp2",
        next_status="approved",
        reason_code="triad_approval",
        actor_role="ceo",
        trace_id="trace-m6-wp2-approve",
    )


def test_initialize_project_returns_policy_denial_when_artifact_type_not_allowed(
    tmp_path: Path,
) -> None:
    artifact_repository = InMemoryProjectArtifactRepository(
        system_root=tmp_path / "system_root",
        policy=ProjectDocumentPolicy(
            allowed_type_caps={"project_charter": 1, "success_metrics": 1},
            total_active_document_cap=20,
        ),
    )
    repository = InMemoryGovernanceRepository(artifact_repository=artifact_repository)
    _seed_approved_project(repository)

    with pytest.raises(GovernanceRepositoryError) as exc:
        repository.initialize_project(
            project_id="project_m6_wp2",
            objective="Deliver governed project documentation persistence",
            budget_currency_total=120.0,
            budget_quota_total=5000.0,
            metric_plan={"delivery": "mvp_acceptance_pass"},
            workforce_plan={"project_manager": "1"},
            actor_id="cwo_1",
            actor_role="cwo",
            trace_id="trace-m6-wp2-init",
        )

    assert exc.value.code == "governance_project_artifact_policy_denied"
