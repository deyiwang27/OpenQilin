"""M13-WP8: Secretary and Routing Spec Alignment unit tests.

Coverage:
- Routing table: MUTATION in executive/leadership_council → cso
- Routing table: ADMIN in executive/leadership_council → cso
- Routing table: DISCUSSION in executive/leadership_council → secretary
- Routing table: QUERY in executive/leadership_council → secretary
- Routing table: governance channel → secretary (not cso) for MUTATION
- Routing table: project channel → project_manager (unchanged)
- SecretaryResponse includes policy_version, policy_hash, rule_ids (AUTH-004, AUTH-005)
- SecretaryDataAccessService.get_project_snapshot: returns snapshot when project found
- SecretaryDataAccessService.get_project_snapshot: returns None when project missing
- SecretaryDataAccessService.get_task_runtime_context: returns context when task found
- SecretaryDataAccessService.get_dashboard_summary: returns zeroed summary on error
- SecretaryAgent with data_access enriches prompt when project_id present
- bootstrap_institutional_agents: secretary is in institutional agents
- bootstrap_institutional_agents: secretary with command agent_type rejected
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from openqilin.agents.secretary.data_access import (
    DashboardSummary,
    ProjectSnapshot,
    SecretaryDataAccessService,
    TaskRuntimeContext,
)
from openqilin.agents.secretary.models import SecretaryResponse
from openqilin.control_plane.grammar.free_text_router import FreeTextRouter
from openqilin.control_plane.grammar.models import ChatContext, IntentClass
from openqilin.data_access.repositories.agent_registry import AgentRegistryRepositoryError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(chat_class: str, project_id: str | None = None) -> ChatContext:
    return ChatContext(chat_class=chat_class, channel_id="ch-001", project_id=project_id)


def _router() -> FreeTextRouter:
    return FreeTextRouter()


# ---------------------------------------------------------------------------
# FreeTextRouter routing table tests
# ---------------------------------------------------------------------------


class TestFreeTextRouterMutationAdminRouting:
    def test_mutation_in_executive_routes_to_cso(self) -> None:
        hint = _router().resolve(IntentClass.MUTATION, _ctx("executive"))
        assert hint.target_role == "cso"

    def test_admin_in_executive_routes_to_cso(self) -> None:
        hint = _router().resolve(IntentClass.ADMIN, _ctx("executive"))
        assert hint.target_role == "cso"

    def test_mutation_in_leadership_council_routes_to_cso(self) -> None:
        hint = _router().resolve(IntentClass.MUTATION, _ctx("leadership_council"))
        assert hint.target_role == "cso"

    def test_admin_in_leadership_council_routes_to_cso(self) -> None:
        hint = _router().resolve(IntentClass.ADMIN, _ctx("leadership_council"))
        assert hint.target_role == "cso"

    def test_mutation_in_governance_channel_routes_to_secretary(self) -> None:
        """governance channel does not route MUTATION to CSO (CSO_ROUTING_CLASSES only)."""
        hint = _router().resolve(IntentClass.MUTATION, _ctx("governance"))
        assert hint.target_role == "secretary"

    def test_discussion_in_executive_routes_to_secretary(self) -> None:
        hint = _router().resolve(IntentClass.DISCUSSION, _ctx("executive"))
        assert hint.target_role == "secretary"

    def test_query_in_executive_routes_to_secretary(self) -> None:
        hint = _router().resolve(IntentClass.QUERY, _ctx("executive"))
        assert hint.target_role == "secretary"

    def test_discussion_in_leadership_council_routes_to_secretary(self) -> None:
        hint = _router().resolve(IntentClass.DISCUSSION, _ctx("leadership_council"))
        assert hint.target_role == "secretary"

    def test_query_in_leadership_council_routes_to_secretary(self) -> None:
        hint = _router().resolve(IntentClass.QUERY, _ctx("leadership_council"))
        assert hint.target_role == "secretary"

    def test_project_channel_routes_to_project_manager(self) -> None:
        hint = _router().resolve(IntentClass.DISCUSSION, _ctx("project", "proj-001"))
        assert hint.target_role == "project_manager"
        assert hint.project_id == "proj-001"

    def test_direct_channel_routes_to_secretary(self) -> None:
        hint = _router().resolve(IntentClass.QUERY, _ctx("direct"))
        assert hint.target_role == "secretary"

    def test_cso_routing_preserves_project_id(self) -> None:
        hint = _router().resolve(IntentClass.MUTATION, _ctx("executive", "proj-001"))
        assert hint.target_role == "cso"
        assert hint.project_id == "proj-001"


# ---------------------------------------------------------------------------
# SecretaryResponse audit metadata (AUTH-004, AUTH-005)
# ---------------------------------------------------------------------------


class TestSecretaryResponseAuditMetadata:
    def test_secretary_response_has_policy_version(self) -> None:
        resp = SecretaryResponse(
            advisory_text="Hello",
            intent_confirmed=IntentClass.QUERY,
            routing_suggestion=None,
            trace_id="trace-001",
        )
        assert resp.policy_version == "v2"

    def test_secretary_response_has_policy_hash(self) -> None:
        resp = SecretaryResponse(
            advisory_text="Hello",
            intent_confirmed=IntentClass.QUERY,
            routing_suggestion=None,
            trace_id="trace-001",
        )
        assert resp.policy_hash == "secretary-advisory-v1"

    def test_secretary_response_has_rule_ids(self) -> None:
        resp = SecretaryResponse(
            advisory_text="Hello",
            intent_confirmed=IntentClass.QUERY,
            routing_suggestion=None,
            trace_id="trace-001",
        )
        assert "AUTH-004" in resp.rule_ids
        assert "AUTH-005" in resp.rule_ids

    def test_secretary_response_rule_ids_is_tuple(self) -> None:
        resp = SecretaryResponse(
            advisory_text="Hello",
            intent_confirmed=IntentClass.QUERY,
            routing_suggestion=None,
            trace_id="trace-001",
        )
        assert isinstance(resp.rule_ids, tuple)


# ---------------------------------------------------------------------------
# SecretaryDataAccessService
# ---------------------------------------------------------------------------


def _make_task(
    task_id: str = "t-001", status: str = "running", project_id: str | None = "proj-001"
) -> object:
    task = MagicMock()
    task.task_id = task_id
    task.status = status
    task.project_id = project_id
    task.principal_id = "owner_001"
    task.trace_id = "trace-001"
    task.outcome_error_code = None
    return task


def _make_project(project_id: str = "proj-001", status: str = "active") -> object:
    project = MagicMock()
    project.status = status
    project.title = "Test Project"
    return project


class TestSecretaryDataAccessService:
    def _make_service(
        self,
        project: object | None = None,
        tasks: tuple = (),
    ) -> SecretaryDataAccessService:
        gov_repo = MagicMock()
        gov_repo.get_project.return_value = project
        state_repo = MagicMock()
        state_repo.list_tasks.return_value = tasks
        state_repo.get_task_by_id.return_value = tasks[0] if tasks else None
        return SecretaryDataAccessService(
            governance_repo=gov_repo,
            runtime_state_repo=state_repo,
        )

    def test_get_project_snapshot_returns_snapshot_when_found(self) -> None:
        tasks = (_make_task(status="running"), _make_task(task_id="t-002", status="blocked"))
        service = self._make_service(project=_make_project(), tasks=tasks)

        snapshot = service.get_project_snapshot("proj-001")

        assert isinstance(snapshot, ProjectSnapshot)
        assert snapshot.project_id == "proj-001"
        assert snapshot.status == "active"
        assert snapshot.active_task_count == 1
        assert snapshot.blocked_task_count == 1

    def test_get_project_snapshot_returns_none_when_not_found(self) -> None:
        service = self._make_service(project=None)

        result = service.get_project_snapshot("proj-missing")

        assert result is None

    def test_get_project_snapshot_returns_none_on_read_error(self) -> None:
        gov_repo = MagicMock()
        gov_repo.get_project.side_effect = RuntimeError("db down")
        service = SecretaryDataAccessService(
            governance_repo=gov_repo,
            runtime_state_repo=MagicMock(),
        )

        result = service.get_project_snapshot("proj-001")

        assert result is None

    def test_get_task_runtime_context_returns_context_when_found(self) -> None:
        task = _make_task()
        service = self._make_service(tasks=(task,))

        ctx = service.get_task_runtime_context("t-001")

        assert isinstance(ctx, TaskRuntimeContext)
        assert ctx.task_id == "t-001"
        assert ctx.status == "running"

    def test_get_task_runtime_context_returns_none_when_not_found(self) -> None:
        state_repo = MagicMock()
        state_repo.get_task_by_id.return_value = None
        service = SecretaryDataAccessService(
            governance_repo=MagicMock(),
            runtime_state_repo=state_repo,
        )

        result = service.get_task_runtime_context("t-missing")

        assert result is None

    def test_get_dashboard_summary_returns_counts(self) -> None:
        tasks = (
            _make_task(task_id="t-1", status="running"),
            _make_task(task_id="t-2", status="blocked"),
            _make_task(task_id="t-3", status="failed"),
            _make_task(task_id="t-4", status="completed"),
        )
        service = self._make_service(tasks=tasks)

        summary = service.get_dashboard_summary()

        assert isinstance(summary, DashboardSummary)
        assert summary.active_task_count == 1
        assert summary.blocked_task_count == 1
        assert summary.failed_task_count == 1

    def test_get_dashboard_summary_returns_zeroed_on_error(self) -> None:
        state_repo = MagicMock()
        state_repo.list_tasks.side_effect = RuntimeError("db down")
        service = SecretaryDataAccessService(
            governance_repo=MagicMock(),
            runtime_state_repo=state_repo,
        )

        summary = service.get_dashboard_summary()

        assert summary.active_task_count == 0
        assert summary.blocked_task_count == 0


# ---------------------------------------------------------------------------
# Secretary registration validation (advisory-only profile)
# ---------------------------------------------------------------------------


class TestSecretaryRegistrationValidation:
    def test_bootstrap_includes_secretary_in_institutional_agents(self) -> None:
        from tests.testing.infra_stubs import InMemoryAgentRegistryRepository

        repo = InMemoryAgentRegistryRepository()
        agents = repo.bootstrap_institutional_agents()
        roles = {a.role for a in agents}
        assert "secretary" in roles

    def test_secretary_agent_type_is_institutional(self) -> None:
        from tests.testing.infra_stubs import InMemoryAgentRegistryRepository

        repo = InMemoryAgentRegistryRepository()
        repo.bootstrap_institutional_agents()
        from openqilin.data_access.repositories.agent_registry import AgentRecord

        secretary = repo.get_agent_by_role("secretary")
        assert secretary is not None
        assert isinstance(secretary, AgentRecord)
        assert secretary.agent_type == "institutional"

    def test_secretary_with_command_agent_type_rejected(self) -> None:
        """bootstrap_institutional_agents raises if existing secretary has non-advisory type."""
        from openqilin.data_access.repositories.agent_registry import AgentRecord
        from tests.testing.infra_stubs import InMemoryAgentRegistryRepository

        repo = InMemoryAgentRegistryRepository()
        # Manually inject a secretary record with a forbidden agent_type
        now = datetime.now(tz=UTC)
        repo._agents["secretary"] = AgentRecord(
            agent_id="secretary_core",
            role="secretary",
            agent_type="command",  # forbidden
            status="active",
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(AgentRegistryRepositoryError) as exc_info:
            repo.bootstrap_institutional_agents()

        assert exc_info.value.code == "agent_registry_advisory_only_violation"
        assert "secretary" in exc_info.value.message
