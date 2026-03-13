import pytest

from openqilin.data_access.repositories.governance import (
    GovernanceRepositoryError,
    InMemoryGovernanceRepository,
)


def _seed_active_project(repository: InMemoryGovernanceRepository, project_id: str) -> None:
    repository.create_project(
        project_id=project_id,
        name="Completion Governance",
        objective="Validate completion governance prerequisites",
    )
    repository.transition_project_status(
        project_id=project_id,
        next_status="approved",
        reason_code="triad_approval",
        actor_role="ceo",
        trace_id=f"trace-{project_id}-approve",
    )
    repository.initialize_project(
        project_id=project_id,
        objective="Initialized objective",
        budget_currency_total=10.0,
        budget_quota_total=100.0,
        metric_plan={"delivery": "ok"},
        workforce_plan={"project_manager": "1"},
        actor_id="cwo_1",
        actor_role="cwo",
        trace_id=f"trace-{project_id}-initialize",
    )


def test_completed_transition_requires_completion_report_and_approval_chain() -> None:
    repository = InMemoryGovernanceRepository()
    project_id = "project_m7_completion_guard"
    _seed_active_project(repository, project_id)

    with pytest.raises(GovernanceRepositoryError) as exc:
        repository.transition_project_status(
            project_id=project_id,
            next_status="completed",
            reason_code="complete_without_chain",
            actor_role="cwo",
            trace_id="trace-m7-complete-missing-chain",
        )

    assert exc.value.code == "governance_project_completion_report_missing"


def test_completed_transition_succeeds_after_report_and_cwo_ceo_approvals() -> None:
    repository = InMemoryGovernanceRepository()
    project_id = "project_m7_completion_success"
    _seed_active_project(repository, project_id)
    repository.submit_completion_report(
        project_id=project_id,
        actor_id="pm_1",
        actor_role="project_manager",
        summary="All work packages completed.",
        metric_results={"acceptance": "passed"},
        trace_id="trace-m7-report",
    )
    repository.record_completion_approval(
        project_id=project_id,
        actor_id="cwo_1",
        actor_role="cwo",
        trace_id="trace-m7-approval-cwo",
    )
    project, _ = repository.record_completion_approval(
        project_id=project_id,
        actor_id="ceo_1",
        actor_role="ceo",
        trace_id="trace-m7-approval-ceo",
    )

    assert project.completion_owner_notified_at is not None
    completed = repository.transition_project_status(
        project_id=project_id,
        next_status="completed",
        reason_code="completion_approved_by_cwo_ceo",
        actor_role="cwo",
        trace_id="trace-m7-complete",
    )
    assert completed.status == "completed"


def test_completion_report_submission_rejects_non_project_manager_role() -> None:
    repository = InMemoryGovernanceRepository()
    project_id = "project_m7_completion_report_role"
    _seed_active_project(repository, project_id)

    with pytest.raises(GovernanceRepositoryError) as exc:
        repository.submit_completion_report(
            project_id=project_id,
            actor_id="owner_1",
            actor_role="owner",
            summary="This should fail.",
            metric_results={},
            trace_id="trace-m7-report-denied",
        )

    assert exc.value.code == "governance_project_completion_report_role_forbidden"
