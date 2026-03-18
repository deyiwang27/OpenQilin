import pytest
from pydantic import ValidationError

from openqilin.control_plane.governance.project_lifecycle import (
    ProjectLifecycleError,
    allowed_project_status_transitions,
    assert_project_transition,
    is_terminal_project_status,
    parse_project_status,
)
from openqilin.control_plane.schemas.governance import ProjectLifecycleTransitionRequest
from openqilin.data_access.repositories.governance import GovernanceRepositoryError
from tests.testing.infra_stubs import InMemoryGovernanceRepository


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    (
        ("proposed", "proposed"),
        ("proposed", "approved"),
        ("approved", "active"),
        ("active", "paused"),
        ("active", "completed"),
        ("active", "terminated"),
        ("paused", "active"),
        ("paused", "terminated"),
        ("completed", "archived"),
        ("terminated", "archived"),
    ),
)
def test_assert_project_transition_accepts_canonical_paths(
    current_status: str,
    next_status: str,
) -> None:
    assert assert_project_transition(current_status, next_status) == next_status


@pytest.mark.parametrize(
    ("current_status", "next_status"),
    (
        ("proposed", "active"),
        ("proposed", "terminated"),
        ("approved", "terminated"),
        ("paused", "completed"),
        ("completed", "active"),
        ("completed", "terminated"),
        ("terminated", "active"),
        ("archived", "proposed"),
    ),
)
def test_assert_project_transition_rejects_illegal_paths(
    current_status: str,
    next_status: str,
) -> None:
    with pytest.raises(ProjectLifecycleError) as exc:
        assert_project_transition(current_status, next_status)

    assert exc.value.code == "project_invalid_transition"


def test_parse_project_status_normalizes_case_and_whitespace() -> None:
    assert parse_project_status("  Proposed  ") == "proposed"


def test_parse_project_status_rejects_unknown_status() -> None:
    with pytest.raises(ProjectLifecycleError) as exc:
        parse_project_status("rejected")

    assert exc.value.code == "project_invalid_status"


def test_allowed_project_status_transitions_for_paused_state() -> None:
    assert allowed_project_status_transitions("paused") == ("active", "terminated")


def test_is_terminal_project_status_only_archived() -> None:
    assert is_terminal_project_status("archived") is True
    assert is_terminal_project_status("completed") is False


def test_governance_transition_schema_rejects_illegal_transition() -> None:
    with pytest.raises(ValidationError):
        ProjectLifecycleTransitionRequest(
            project_id="project-m5-001",
            from_status="approved",
            to_status="terminated",
            reason_code="lifecycle_check",
            trace_id="trace-m5-001",
        )


def test_governance_repository_enforces_project_creation_in_proposed_state() -> None:
    repository = InMemoryGovernanceRepository()
    with pytest.raises(GovernanceRepositoryError) as exc:
        repository.create_project(
            project_id="project-m5-001",
            name="M5 Test Project",
            objective="validate lifecycle guards",
            status="approved",
        )

    assert exc.value.code == "governance_project_invalid_create_state"


def test_governance_repository_tracks_transition_history() -> None:
    repository = InMemoryGovernanceRepository()
    project = repository.create_project(
        project_id="project-m5-001",
        name="M5 Test Project",
        objective="validate lifecycle guards",
    )
    approved = repository.transition_project_status(
        project_id=project.project_id,
        next_status="approved",
        reason_code="triad_approval",
        actor_role="ceo",
        trace_id="trace-m5-001",
    )
    active = repository.transition_project_status(
        project_id=project.project_id,
        next_status="active",
        reason_code="project_start",
        actor_role="cwo",
        trace_id="trace-m5-002",
    )

    assert project.status == "proposed"
    assert approved.status == "approved"
    assert active.status == "active"
    assert len(active.transitions) == 2
    assert active.transitions[0].from_status == "proposed"
    assert active.transitions[0].to_status == "approved"
    assert active.transitions[1].from_status == "approved"
    assert active.transitions[1].to_status == "active"


def test_governance_repository_rejects_illegal_transition() -> None:
    repository = InMemoryGovernanceRepository()
    project = repository.create_project(
        project_id="project-m5-001",
        name="M5 Test Project",
        objective="validate lifecycle guards",
    )
    with pytest.raises(GovernanceRepositoryError) as exc:
        repository.transition_project_status(
            project_id=project.project_id,
            next_status="active",
            reason_code="skip_approval",
            actor_role="cwo",
            trace_id="trace-m5-003",
        )

    assert exc.value.code == "project_invalid_transition"
