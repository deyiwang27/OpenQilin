import pytest

from openqilin.control_plane.handlers.governance_handler import (
    GovernanceHandlerError,
    approve_project_proposal,
    submit_proposal_message,
)
from openqilin.data_access.repositories.governance import InMemoryGovernanceRepository


def _seed_project(
    repository: InMemoryGovernanceRepository, project_id: str = "project_m5_wp2"
) -> None:
    repository.create_project(
        project_id=project_id,
        name="M5 Governance Contract",
        objective="Validate proposal discussion and approval APIs.",
    )


def test_submit_proposal_message_accepts_triad_role() -> None:
    repository = InMemoryGovernanceRepository()
    _seed_project(repository)

    message = submit_proposal_message(
        repository=repository,
        project_id="project_m5_wp2",
        actor_id="owner_1",
        actor_role="owner",
        content="Proposal scope is acceptable after revisions.",
        trace_id="trace-m5-wp2-msg",
    )

    assert message.project_id == "project_m5_wp2"
    assert message.actor_role == "owner"
    assert message.content.startswith("Proposal scope")


def test_submit_proposal_message_rejects_non_triad_role() -> None:
    repository = InMemoryGovernanceRepository()
    _seed_project(repository)

    with pytest.raises(GovernanceHandlerError) as exc:
        submit_proposal_message(
            repository=repository,
            project_id="project_m5_wp2",
            actor_id="auditor_1",
            actor_role="auditor",
            content="Trying to discuss as auditor.",
            trace_id="trace-m5-wp2-msg-deny",
        )

    assert exc.value.code == "governance_role_forbidden"


def test_approve_project_proposal_promotes_after_triad_approvals() -> None:
    repository = InMemoryGovernanceRepository()
    _seed_project(repository)

    first = approve_project_proposal(
        repository=repository,
        project_id="project_m5_wp2",
        actor_id="owner_1",
        actor_role="owner",
        trace_id="trace-m5-wp2-approve-owner",
    )
    second = approve_project_proposal(
        repository=repository,
        project_id="project_m5_wp2",
        actor_id="ceo_1",
        actor_role="ceo",
        trace_id="trace-m5-wp2-approve-ceo",
    )
    third = approve_project_proposal(
        repository=repository,
        project_id="project_m5_wp2",
        actor_id="cwo_1",
        actor_role="cwo",
        trace_id="trace-m5-wp2-approve-cwo",
    )

    assert first.project.status == "proposed"
    assert second.project.status == "proposed"
    assert third.project.status == "approved"
    assert third.approval_roles == ("ceo", "cwo", "owner")


def test_approve_project_proposal_rejects_non_triad_role() -> None:
    repository = InMemoryGovernanceRepository()
    _seed_project(repository)

    with pytest.raises(GovernanceHandlerError) as exc:
        approve_project_proposal(
            repository=repository,
            project_id="project_m5_wp2",
            actor_id="auditor_1",
            actor_role="auditor",
            trace_id="trace-m5-wp2-approve-auditor",
        )

    assert exc.value.code == "governance_approval_role_forbidden"
