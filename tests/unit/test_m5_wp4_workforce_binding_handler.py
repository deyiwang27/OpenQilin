import pytest

from openqilin.control_plane.handlers.governance_handler import (
    GovernanceHandlerError,
    bind_workforce_template_by_cwo,
)
from tests.testing.infra_stubs import InMemoryGovernanceRepository


def _seed_active_project(repository: InMemoryGovernanceRepository) -> None:
    repository.create_project(
        project_id="project_m5_wp4",
        name="M5 Workforce Binding",
        objective="Seed objective",
    )
    repository.transition_project_status(
        project_id="project_m5_wp4",
        next_status="approved",
        reason_code="triad_approval",
        actor_role="ceo",
        trace_id="trace-m5-wp4-approve",
    )
    repository.initialize_project(
        project_id="project_m5_wp4",
        objective="Initialized objective",
        budget_currency_total=100.0,
        budget_quota_total=1000.0,
        metric_plan={"delivery": "ok"},
        workforce_plan={"project_manager": "1"},
        actor_id="cwo_1",
        actor_role="cwo",
        trace_id="trace-m5-wp4-init",
    )


def test_bind_workforce_template_creates_active_project_manager_binding() -> None:
    repository = InMemoryGovernanceRepository()
    _seed_active_project(repository)

    outcome = bind_workforce_template_by_cwo(
        repository=repository,
        project_id="project_m5_wp4",
        actor_id="cwo_1",
        actor_role="cwo",
        trace_id="trace-m5-wp4-bind-project-manager",
        role="project_manager",
        template_id="project_manager_template_v1",
        llm_routing_profile="dev_gemini_free",
        system_prompt=(
            "You are Project Manager. Mandatory operations: milestone planning, "
            "task decomposition, task assignment, progress reporting."
        ),
    )

    assert outcome.role == "project_manager"
    assert outcome.binding_status == "active"
    assert len(outcome.system_prompt_hash) == 64
    assert outcome.mandatory_operations == (
        "milestone_planning",
        "progress_reporting",
        "task_assignment",
        "task_decomposition",
    )
    project = repository.get_project("project_m5_wp4")
    assert project is not None
    assert project.workforce_bindings[-1].mandatory_operations == outcome.mandatory_operations


def test_bind_workforce_template_keeps_domain_leader_declared_disabled() -> None:
    repository = InMemoryGovernanceRepository()
    _seed_active_project(repository)

    outcome = bind_workforce_template_by_cwo(
        repository=repository,
        project_id="project_m5_wp4",
        actor_id="cwo_1",
        actor_role="cwo",
        trace_id="trace-m5-wp4-bind-dl",
        role="domain_leader",
        template_id="domain_leader_template_v1",
        llm_routing_profile="dev_gemini_free",
        system_prompt="You are Domain Leader.",
    )

    assert outcome.role == "domain_leader"
    assert outcome.binding_status == "declared_disabled"
    assert outcome.mandatory_operations == ()


def test_bind_project_manager_template_rejects_missing_mandatory_operations() -> None:
    repository = InMemoryGovernanceRepository()
    _seed_active_project(repository)

    with pytest.raises(GovernanceHandlerError) as exc:
        bind_workforce_template_by_cwo(
            repository=repository,
            project_id="project_m5_wp4",
            actor_id="cwo_1",
            actor_role="cwo",
            trace_id="trace-m6-wp4-bind-missing-ops",
            role="project_manager",
            template_id="project_manager_template_v1",
            llm_routing_profile="dev_gemini_free",
            system_prompt="You are Project Manager.",
        )

    assert exc.value.code == "governance_project_manager_template_missing_operations"


def test_bind_workforce_template_rejects_non_cwo_role() -> None:
    repository = InMemoryGovernanceRepository()
    _seed_active_project(repository)

    with pytest.raises(GovernanceHandlerError) as exc:
        bind_workforce_template_by_cwo(
            repository=repository,
            project_id="project_m5_wp4",
            actor_id="owner_1",
            actor_role="owner",
            trace_id="trace-m5-wp4-bind-denied",
            role="project_manager",
            template_id="project_manager_template_v1",
            llm_routing_profile="dev_gemini_free",
            system_prompt=(
                "You are Project Manager. Mandatory operations: milestone planning, "
                "task decomposition, task assignment, progress reporting."
            ),
        )

    assert exc.value.code == "governance_role_forbidden"
