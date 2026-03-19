"""M14-WP6 - Specialist Agent and task execution engine unit tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from openqilin.agents.specialist.agent import SpecialistAgent
from openqilin.agents.specialist.models import (
    SpecialistDispatchAuthError,
    SpecialistRequest,
)
from openqilin.agents.specialist.task_executor import SpecialistTaskExecutor
from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.data_access.repositories.task_execution_results import TaskExecutionResult
from openqilin.observability.testing.stubs import InMemoryAuditWriter
from openqilin.task_orchestrator.dispatch.target_selector import select_dispatch_target
from tests.testing.infra_stubs import InMemoryProjectArtifactRepository


@dataclass
class _StubTaskExecutionResultsRepository:
    results: list[TaskExecutionResult]

    def write_result(self, result: TaskExecutionResult) -> TaskExecutionResult:
        self.results.append(result)
        return result

    def get_results_for_task(self, task_id: str) -> tuple[TaskExecutionResult, ...]:
        return tuple(result for result in self.results if result.task_id == task_id)


def _make_agent(
    tmp_path: Path,
) -> tuple[
    SpecialistAgent,
    _StubTaskExecutionResultsRepository,
    InMemoryProjectArtifactRepository,
    InMemoryAuditWriter,
]:
    result_repo = _StubTaskExecutionResultsRepository(results=[])
    governance_repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
    audit_writer = InMemoryAuditWriter()
    agent = SpecialistAgent(
        executor=SpecialistTaskExecutor(),
        task_execution_results_repo=result_repo,
        governance_repo=governance_repo,
        audit_writer=audit_writer,
        trace_id_factory=lambda: "generated-result-id",
    )
    return agent, result_repo, governance_repo, audit_writer


def _request(
    *,
    task_id: str = "task-001",
    project_id: str = "proj-001",
    task_description: str = "execute task",
    approved_tools: tuple[str, ...] = (),
    dispatch_source_role: str = "project_manager",
    trace_id: str = "trace-001",
) -> SpecialistRequest:
    return SpecialistRequest(
        task_id=task_id,
        project_id=project_id,
        task_description=task_description,
        approved_tools=approved_tools,
        dispatch_source_role=dispatch_source_role,
        trace_id=trace_id,
    )


def _task_record(*, target: str, command: str) -> TaskRecord:
    return TaskRecord(
        task_id="task-001",
        request_id="request-001",
        trace_id="trace-001",
        principal_id="principal-001",
        principal_role="project_manager",
        trust_domain="project",
        connector="internal",
        command=command,
        target=target,
        args=(),
        metadata=(),
        project_id="proj-001",
        idempotency_key="idem-001",
        status="queued",
        created_at=datetime.now(tz=UTC),
    )


class TestDispatchEnforcement:
    def test_direct_owner_request_rejected(self, tmp_path: Path) -> None:
        agent, _, _, _ = _make_agent(tmp_path)

        try:
            agent.handle(_request(dispatch_source_role="owner"))
        except SpecialistDispatchAuthError:
            return
        raise AssertionError("expected SpecialistDispatchAuthError")

    def test_empty_task_id_rejected(self, tmp_path: Path) -> None:
        agent, _, _, _ = _make_agent(tmp_path)

        try:
            agent.handle(_request(task_id=""))
        except SpecialistDispatchAuthError:
            return
        raise AssertionError("expected SpecialistDispatchAuthError")

    def test_pm_dispatch_accepted(self, tmp_path: Path) -> None:
        agent, _, _, _ = _make_agent(tmp_path)

        response = agent.handle(_request())

        assert response.execution_status == "completed"

    def test_whitespace_normalized_source_role(self, tmp_path: Path) -> None:
        agent, _, _, _ = _make_agent(tmp_path)

        response = agent.handle(_request(dispatch_source_role="  project_manager  "))

        assert response.execution_status == "completed"


class TestExecution:
    def test_task_result_written_not_project_artifact(self, tmp_path: Path) -> None:
        agent, result_repo, governance_repo, _ = _make_agent(tmp_path)

        response = agent.handle(_request(task_description="complete the assigned task"))

        assert response.execution_status == "completed"
        assert len(result_repo.get_results_for_task("task-001")) == 1
        assert governance_repo.list_project_artifacts("proj-001") == ()

    def test_unapproved_tool_blocked(self, tmp_path: Path) -> None:
        agent, _, _, _ = _make_agent(tmp_path)

        response = agent.handle(
            _request(
                task_description="run task [tools: write_file]",
                approved_tools=("read_file",),
            )
        )

        assert response.execution_status == "blocked"
        assert "tool_not_authorized" in (response.blocker or "")

    def test_approved_tool_passes(self, tmp_path: Path) -> None:
        agent, _, _, _ = _make_agent(tmp_path)

        response = agent.handle(
            _request(
                task_description="run task [tools: read_file]",
                approved_tools=("read_file",),
            )
        )

        assert response.execution_status == "completed"

    def test_artifact_id_is_result_id(self, tmp_path: Path) -> None:
        agent, result_repo, _, _ = _make_agent(tmp_path)

        response = agent.handle(_request())

        assert response.artifact_id == result_repo.get_results_for_task("task-001")[0].result_id

    def test_audit_event_written_on_completion(self, tmp_path: Path) -> None:
        agent, _, _, audit_writer = _make_agent(tmp_path)

        agent.handle(_request())

        assert audit_writer.get_events()[-1].event_type == "specialist_task_completed"


class TestClarification:
    def test_clarification_needed_returns_blocker(self, tmp_path: Path) -> None:
        agent, _, _, _ = _make_agent(tmp_path)

        response = agent.handle(
            _request(task_description="task [clarification_needed: need DL input]")
        )

        assert response.execution_status == "clarification_needed"
        assert (response.blocker or "").startswith("clarification_needed:")

    def test_clarification_needed_no_artifact_written(self, tmp_path: Path) -> None:
        agent, result_repo, _, _ = _make_agent(tmp_path)

        response = agent.handle(
            _request(task_description="task [clarification_needed: need DL input]")
        )

        assert response.execution_status == "clarification_needed"
        assert result_repo.get_results_for_task("task-001") == ()


class TestBehavioralViolation:
    def test_behavioral_violation_emits_audit_event(self, tmp_path: Path) -> None:
        agent, _, _, audit_writer = _make_agent(tmp_path)

        agent.report_behavioral_violation(
            task_id="task-001",
            project_id="proj-001",
            description="specialist violated execution boundaries",
            trace_id="trace-violation",
        )

        event = audit_writer.get_events()[-1]
        payload = dict(event.payload)
        assert event.event_type == "behavioral_violation"
        assert payload["current_owner_role"] == "specialist"
        assert payload["next_owner_role"] == "project_manager"

    def test_behavioral_violation_writes_auditor_finding(self, tmp_path: Path) -> None:
        agent, _, governance_repo, _ = _make_agent(tmp_path)

        storage_uri = agent.report_behavioral_violation(
            task_id="task-001",
            project_id="proj-001",
            description="specialist violated execution boundaries",
            trace_id="trace-violation",
        )

        document = governance_repo.read_latest_artifact("system", "auditor_finding")
        assert document is not None
        assert document.pointer.storage_uri == storage_uri
        payload = json.loads(document.content)
        assert payload["project_id"] == "proj-001"


class TestTargetSelector:
    def test_specialist_target_routes_to_specialist(self) -> None:
        task = _task_record(target="specialist", command="execute_specialist_task")

        assert select_dispatch_target(task) == "specialist"

    def test_specialist_target_takes_priority_over_command_prefix(self) -> None:
        task = _task_record(target="specialist", command="llm_foo")

        assert select_dispatch_target(task) == "specialist"

    def test_llm_command_routes_to_llm(self) -> None:
        task = _task_record(target="secretary", command="llm_ask")

        assert select_dispatch_target(task) == "llm"

    def test_sandbox_default(self) -> None:
        task = _task_record(target="secretary", command="run_without_prefix")

        assert select_dispatch_target(task) == "sandbox"
