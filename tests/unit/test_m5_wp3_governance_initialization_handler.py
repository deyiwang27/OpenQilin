import pytest

from openqilin.control_plane.handlers.governance_handler import (
    GovernanceHandlerError,
    initialize_project_by_cwo,
)
from openqilin.data_access.repositories.governance import InMemoryGovernanceRepository


def _seed_approved_project(repository: InMemoryGovernanceRepository) -> None:
    repository.create_project(
        project_id="project_m5_wp3",
        name="M5 Initialization",
        objective="Seed objective",
    )
    repository.transition_project_status(
        project_id="project_m5_wp3",
        next_status="approved",
        reason_code="triad_approval",
        actor_role="ceo",
        trace_id="trace-m5-wp3-approve",
    )


def test_initialize_project_by_cwo_promotes_project_to_active() -> None:
    repository = InMemoryGovernanceRepository()
    _seed_approved_project(repository)

    outcome = initialize_project_by_cwo(
        repository=repository,
        project_id="project_m5_wp3",
        actor_id="cwo_1",
        actor_role="cwo",
        trace_id="trace-m5-wp3-init",
        objective="Deliver MVP governance runtime",
        budget_currency_total=120.0,
        budget_quota_total=5000.0,
        metric_plan={"delivery": "mvp_acceptance_pass"},
        workforce_plan={"pm": "1", "specialist": "2"},
    )

    assert outcome.project.status == "active"
    assert outcome.project.initialization is not None
    assert outcome.project.initialization.objective == "Deliver MVP governance runtime"
    assert outcome.project.initialization.budget_currency_total == 120.0
    assert outcome.project.initialization.budget_quota_total == 5000.0


def test_initialize_project_by_cwo_rejects_non_cwo_role() -> None:
    repository = InMemoryGovernanceRepository()
    _seed_approved_project(repository)

    with pytest.raises(GovernanceHandlerError) as exc:
        initialize_project_by_cwo(
            repository=repository,
            project_id="project_m5_wp3",
            actor_id="owner_1",
            actor_role="owner",
            trace_id="trace-m5-wp3-init-denied",
            objective="Should fail",
            budget_currency_total=1.0,
            budget_quota_total=1.0,
            metric_plan={},
            workforce_plan={},
        )

    assert exc.value.code == "governance_role_forbidden"


def test_initialize_project_by_cwo_requires_approved_project() -> None:
    repository = InMemoryGovernanceRepository()
    repository.create_project(
        project_id="project_m5_wp3",
        name="M5 Initialization",
        objective="Seed objective",
    )

    with pytest.raises(GovernanceHandlerError) as exc:
        initialize_project_by_cwo(
            repository=repository,
            project_id="project_m5_wp3",
            actor_id="cwo_1",
            actor_role="cwo",
            trace_id="trace-m5-wp3-init-not-approved",
            objective="Should fail",
            budget_currency_total=1.0,
            budget_quota_total=1.0,
            metric_plan={},
            workforce_plan={},
        )

    assert exc.value.code == "governance_project_not_approved"
