"""M15-WP4 unit tests for M-4 and M-5 bug fixes."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from openqilin.budget_runtime.models import (
    BudgetConfigurationError,
    BudgetReservationResult,
)
from openqilin.data_access.repositories.agent_registry import AgentRecord
from openqilin.data_access.repositories.postgres.agent_registry_repository import (
    _INSTITUTIONAL_ROLES,
    PostgresAgentRegistryRepository,
)
from openqilin.execution_sandbox.tools.contracts import ToolCallContext, ToolResult
from openqilin.execution_sandbox.tools.write_tools import GovernedWriteToolService


def _tool_context() -> ToolCallContext:
    return ToolCallContext(
        task_id="task-001",
        request_id="req-001",
        trace_id="trace-001",
        principal_id="principal-001",
        principal_role="ceo",
        recipient_role="ceo",
        recipient_id=None,
        project_id="project-001",
    )


def _allow_budget_reservation() -> BudgetReservationResult:
    return BudgetReservationResult(
        decision="allow",
        reason_code="budget_ok",
        reason_message="budget reservation approved",
        reservation_id="resv-001",
        remaining_units=999,
        budget_version="budget-v1",
    )


def _ok_tool_result(context: ToolCallContext) -> ToolResult:
    return ToolResult(
        decision="ok",
        tool_name="append_decision_log",
        tool_call_id="tool-call-001",
        trace_id=context.trace_id,
        request_id=context.request_id,
        data={"ok": True},
        sources=(),
        message="ok",
    )


def test_budget_client_none_raises_budget_configuration_error() -> None:
    service = GovernedWriteToolService(
        governance_repository=MagicMock(),
        project_artifact_repository=MagicMock(),
        audit_writer=MagicMock(),
        budget_runtime_client=None,
    )

    with pytest.raises(BudgetConfigurationError, match="budget_runtime_client is required"):
        service.call_tool(
            tool_name="append_decision_log",
            arguments={"project_id": "project-001", "content": "decision"},
            context=_tool_context(),
        )


def test_budget_client_none_does_not_proceed_to_tool_handler() -> None:
    governance_repository = MagicMock()
    project_artifact_repository = MagicMock()
    service = GovernedWriteToolService(
        governance_repository=governance_repository,
        project_artifact_repository=project_artifact_repository,
        audit_writer=MagicMock(),
        budget_runtime_client=None,
    )
    append_handler = MagicMock(return_value=_ok_tool_result(_tool_context()))
    service._tool_append_decision_log = append_handler  # type: ignore[method-assign]

    with pytest.raises(BudgetConfigurationError):
        service.call_tool(
            tool_name="append_decision_log",
            arguments={"project_id": "project-001", "content": "decision"},
            context=_tool_context(),
        )

    append_handler.assert_not_called()
    governance_repository.get_project.assert_not_called()
    project_artifact_repository.write_project_artifact.assert_not_called()


def test_budget_client_present_proceeds_normally() -> None:
    context = _tool_context()
    budget_runtime_client = MagicMock()
    budget_runtime_client.reserve.return_value = _allow_budget_reservation()
    service = GovernedWriteToolService(
        governance_repository=MagicMock(),
        project_artifact_repository=MagicMock(),
        audit_writer=MagicMock(),
        budget_runtime_client=budget_runtime_client,
    )
    append_handler = MagicMock(return_value=_ok_tool_result(context))
    service._tool_append_decision_log = append_handler  # type: ignore[method-assign]

    result = service.call_tool(
        tool_name="append_decision_log",
        arguments={"project_id": "project-001", "content": "decision"},
        context=context,
    )

    assert result.decision == "ok"
    budget_runtime_client.reserve.assert_called_once()
    append_handler.assert_called_once()


def _agent_record(*, role: str, status: str = "active") -> AgentRecord:
    now = datetime.now(tz=UTC)
    return AgentRecord(
        agent_id=f"{role}_core",
        role=role,
        agent_type="institutional",
        status=status,
        created_at=now,
        updated_at=now,
    )


def _make_repo_with_session_mocks() -> tuple[PostgresAgentRegistryRepository, MagicMock, MagicMock]:
    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__enter__.return_value = session
    session_cm.__exit__.return_value = None
    session_factory = MagicMock(return_value=session_cm)
    repo = PostgresAgentRegistryRepository(session_factory=session_factory)
    repo.list_agents = MagicMock(return_value=())  # type: ignore[method-assign]
    return repo, session, session_factory


def test_bootstrap_twice_produces_one_record_per_role() -> None:
    repo, session, session_factory = _make_repo_with_session_mocks()
    existing_records = [_agent_record(role=role) for role in _INSTITUTIONAL_ROLES]
    repo.get_agent_by_role = MagicMock(  # type: ignore[method-assign]
        side_effect=[None] * len(_INSTITUTIONAL_ROLES) + existing_records
    )

    repo.bootstrap_institutional_agents()
    assert session.execute.call_count == len(_INSTITUTIONAL_ROLES)

    session.execute.reset_mock()
    session_factory.reset_mock()
    repo.bootstrap_institutional_agents()

    session.execute.assert_not_called()
    session_factory.assert_not_called()


def test_bootstrap_does_not_overwrite_existing_inactive_agent() -> None:
    repo, session, _ = _make_repo_with_session_mocks()
    repo.get_agent_by_role = MagicMock(  # type: ignore[method-assign]
        side_effect=[_agent_record(role=role, status="inactive") for role in _INSTITUTIONAL_ROLES]
    )

    repo.bootstrap_institutional_agents()

    session.execute.assert_not_called()
    session.commit.assert_not_called()


def test_bootstrap_inserts_when_agent_missing() -> None:
    repo, session, _ = _make_repo_with_session_mocks()
    repo.get_agent_by_role = MagicMock(  # type: ignore[method-assign]
        side_effect=[None] * len(_INSTITUTIONAL_ROLES)
    )

    repo.bootstrap_institutional_agents()

    assert session.execute.call_count == len(_INSTITUTIONAL_ROLES)
    assert session.commit.call_count == len(_INSTITUTIONAL_ROLES)
    for call in session.execute.call_args_list:
        statement = call.args[0]
        statement_text = getattr(statement, "text", str(statement))
        assert "INSERT INTO agents" in statement_text
        assert "UPDATE agents SET status" not in statement_text
