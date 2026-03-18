"""M14-WP1 — Project Manager Agent unit tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from openqilin.agents.project_manager.agent import ProjectManagerAgent
from openqilin.agents.project_manager.artifact_writer import PMProjectArtifactWriter
from openqilin.agents.project_manager.models import (
    PMProjectContextError,
    PMWriteNotAllowedError,
    ProjectManagerRequest,
)
from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.llm_gateway.schemas.requests import LlmPolicyContext
from openqilin.llm_gateway.schemas.responses import LlmGatewayResponse
from openqilin.task_orchestrator.admission.envelope_validator import AdmissionEnvelope
from openqilin.task_orchestrator.services.lifecycle_service import TaskLifecycleService
from tests.testing.infra_stubs import (
    InMemoryProjectArtifactRepository,
    InMemoryRuntimeStateRepository,
)

_POLICY_CONTEXT = LlmPolicyContext(
    policy_version="v2",
    policy_hash="test-policy",
    rule_ids=(),
)


def _llm_response(text: str) -> LlmGatewayResponse:
    return LlmGatewayResponse(
        request_id="req-1",
        trace_id="trace-1",
        decision="served",
        model_selected="gemini-test",
        usage=None,
        cost=None,
        budget_usage=None,
        budget_context_effective=None,
        quota_limit_source="policy_guardrail",
        latency_ms=1,
        policy_context=_POLICY_CONTEXT,
        generated_text=text,
    )


def _make_llm(text: str) -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = _llm_response(text)
    return llm


@dataclass
class _Snapshot:
    project_id: str
    status: str
    title: str | None = "Project Test"
    active_task_count: int = 3
    blocked_task_count: int = 1


class _DispatchServiceStub:
    def __init__(self, runtime_repo: InMemoryRuntimeStateRepository) -> None:
        self._lifecycle_service = TaskLifecycleService(runtime_state_repo=runtime_repo)
        self.dispatched_tasks: list[TaskRecord] = []

    def dispatch_admitted_task(
        self,
        task: TaskRecord,
        *,
        policy_version: str = "v2",
        policy_hash: str = "project-manager-v1",
        rule_ids: tuple[str, ...] = (),
    ) -> None:
        self.dispatched_tasks.append(task)


def _make_data_access(
    *,
    project_status: str = "active",
    runtime_repo: InMemoryRuntimeStateRepository | None = None,
) -> SimpleNamespace:
    repo = runtime_repo or InMemoryRuntimeStateRepository()
    return SimpleNamespace(
        get_project_snapshot=MagicMock(
            return_value=_Snapshot(project_id="proj-001", status=project_status)
        ),
        get_task_runtime_context=MagicMock(return_value=None),
        _runtime_state_repo=repo,
    )


def _make_source_task(
    runtime_repo: InMemoryRuntimeStateRepository,
    *,
    project_id: str = "proj-001",
    trace_id: str = "trace-source",
) -> TaskRecord:
    return runtime_repo.create_task_from_envelope(
        AdmissionEnvelope(
            request_id="req-source",
            trace_id=trace_id,
            principal_id="owner-001",
            principal_role="owner",
            trust_domain="project",
            connector="internal",
            command="source_task",
            target="project_manager",
            args=(),
            metadata=(),
            project_id=project_id,
            idempotency_key=f"idem-{trace_id}",
        )
    )


def _make_agent(
    *,
    llm_text: str = "Decision: proceed with the current milestone plan.",
    artifact_repo: InMemoryProjectArtifactRepository | None = None,
    runtime_repo: InMemoryRuntimeStateRepository | None = None,
    project_status: str = "active",
) -> tuple[ProjectManagerAgent, InMemoryProjectArtifactRepository, InMemoryRuntimeStateRepository]:
    artifacts = artifact_repo or InMemoryProjectArtifactRepository()
    runtime = runtime_repo or InMemoryRuntimeStateRepository()
    data_access = _make_data_access(project_status=project_status, runtime_repo=runtime)
    agent = ProjectManagerAgent(
        llm_gateway=_make_llm(llm_text),
        artifact_writer=PMProjectArtifactWriter(project_artifact_repo=artifacts),
        data_access=data_access,  # type: ignore[arg-type]
        domain_leader_agent=MagicMock(),
        task_dispatch_service=cast(Any, _DispatchServiceStub(runtime)),
        project_artifact_repo=artifacts,
        trace_id_factory=lambda: "generated-trace",
    )
    return agent, artifacts, runtime


def _request(
    *,
    intent: str,
    project_id: str = "proj-001",
    message: str = "Give me the current status.",
    context: dict[str, object] | None = None,
) -> ProjectManagerRequest:
    return ProjectManagerRequest(
        message=message,
        intent=intent,
        project_id=project_id,
        context=dict(context or {}),
        trace_id="trace-001",
    )


class TestPMProjectContextValidation:
    def test_handle_rejects_missing_project_id(self) -> None:
        agent, _, _ = _make_agent()

        with pytest.raises(PMProjectContextError):
            agent.handle(_request(intent="DISCUSSION", project_id=""))

    def test_handle_rejects_empty_project_id(self) -> None:
        agent, _, _ = _make_agent()

        with pytest.raises(PMProjectContextError):
            agent.handle(_request(intent="QUERY", project_id="   "))


class TestPMStatusReport:
    def test_discussion_returns_status_report_not_advisory(self) -> None:
        agent, _, _ = _make_agent(llm_text="I suggest we review the blockers before proceeding.")

        response = agent.handle(_request(intent="DISCUSSION"))

        assert "I suggest" not in response.advisory_text
        assert response.advisory_text.startswith("Status:")

    def test_query_returns_project_decision(self) -> None:
        agent, _, _ = _make_agent(llm_text="Approve milestone 2 and clear the deployment blocker.")

        response = agent.handle(_request(intent="QUERY", message="What is the project decision?"))

        assert response.action_taken == "project_decision_issued"
        assert "Approve milestone 2" in response.advisory_text


class TestPMSpecialistDispatch:
    def test_dispatch_to_specialist_creates_task_with_target_specialist(self) -> None:
        agent, _, runtime_repo = _make_agent()
        source_task = _make_source_task(runtime_repo)

        task_id = agent.dispatch_to_specialist(source_task.task_id, "proj-001", "trace-dispatch")

        dispatch_service = cast(_DispatchServiceStub, agent._task_dispatch_service)
        created_task = dispatch_service.dispatched_tasks[0]
        assert task_id == created_task.task_id
        assert created_task.target == "specialist"
        assert created_task.project_id == "proj-001"

    def test_dispatch_rejects_cross_project_scope(self) -> None:
        agent, _, runtime_repo = _make_agent()
        source_task = _make_source_task(runtime_repo, project_id="proj-other")

        with pytest.raises(PMProjectContextError, match="AUTH-001"):
            agent.dispatch_to_specialist(source_task.task_id, "proj-001", "trace-dispatch")


class TestPMArtifactWriter:
    def test_write_execution_plan_succeeds_in_active_state(self, tmp_path: Path) -> None:
        repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        writer = PMProjectArtifactWriter(project_artifact_repo=repo)

        pointer = writer.write(
            "proj-001",
            "execution_plan",
            "Execution plan v1",
            "trace-1",
            "active",
        )

        assert pointer.revision_no == 1
        assert repo.read_latest_artifact("proj-001", "execution_plan") is not None

    def test_write_rejects_project_charter(self, tmp_path: Path) -> None:
        writer = PMProjectArtifactWriter(
            project_artifact_repo=InMemoryProjectArtifactRepository(
                system_root=tmp_path / "artifacts"
            )
        )

        with pytest.raises(PMWriteNotAllowedError):
            writer.write("proj-001", "project_charter", "nope", "trace-1", "active")

    def test_write_rejects_workforce_plan(self, tmp_path: Path) -> None:
        writer = PMProjectArtifactWriter(
            project_artifact_repo=InMemoryProjectArtifactRepository(
                system_root=tmp_path / "artifacts"
            )
        )

        with pytest.raises(PMWriteNotAllowedError):
            writer.write("proj-001", "workforce_plan", "nope", "trace-1", "active")

    def test_write_rejects_scope_statement_without_approval_evidence(self, tmp_path: Path) -> None:
        writer = PMProjectArtifactWriter(
            project_artifact_repo=InMemoryProjectArtifactRepository(
                system_root=tmp_path / "artifacts"
            )
        )

        with pytest.raises(PMWriteNotAllowedError):
            writer.write("proj-001", "scope_statement", "scope", "trace-1", "active")

    def test_write_scope_statement_with_approval_evidence_succeeds(self, tmp_path: Path) -> None:
        writer = PMProjectArtifactWriter(
            project_artifact_repo=InMemoryProjectArtifactRepository(
                system_root=tmp_path / "artifacts"
            )
        )

        pointer = writer.write(
            "proj-001",
            "scope_statement",
            "approved scope",
            "trace-1",
            "active",
            approval_evidence={"approval_roles": ("ceo", "cwo")},
        )

        assert pointer.revision_no == 1

    def test_write_rejects_when_project_not_active(self, tmp_path: Path) -> None:
        writer = PMProjectArtifactWriter(
            project_artifact_repo=InMemoryProjectArtifactRepository(
                system_root=tmp_path / "artifacts"
            )
        )

        with pytest.raises(PMWriteNotAllowedError):
            writer.write("proj-001", "execution_plan", "plan", "trace-1", "paused")

    def test_progress_report_is_append_only(self, tmp_path: Path) -> None:
        repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        writer = PMProjectArtifactWriter(project_artifact_repo=repo)

        first = writer.write("proj-001", "progress_report", "progress 1", "trace-1", "active")
        second = writer.write("proj-001", "progress_report", "progress 2", "trace-2", "active")

        assert (first.revision_no, second.revision_no) == (1, 2)

    def test_decision_log_is_append_only(self, tmp_path: Path) -> None:
        repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        writer = PMProjectArtifactWriter(project_artifact_repo=repo)

        first = writer.write("proj-001", "decision_log", "decision 1", "trace-1", "active")
        second = writer.write("proj-001", "decision_log", "decision 2", "trace-2", "active")

        assert (first.revision_no, second.revision_no) == (1, 2)

    def test_completion_report_is_append_only(self, tmp_path: Path) -> None:
        repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        writer = PMProjectArtifactWriter(project_artifact_repo=repo)

        first = writer.write_completion_report("proj-001", "completion 1", "trace-1", "active")
        second = writer.write_completion_report("proj-001", "completion 2", "trace-2", "active")

        assert (first.revision_no, second.revision_no) == (1, 2)


class TestPMDLEscalation:
    def test_escalate_to_dl_returns_synthesised_reply(self) -> None:
        agent, _, _ = _make_agent()
        agent._domain_leader_agent = MagicMock()  # type: ignore[attr-defined]
        agent._domain_leader_agent.handle_escalation.return_value = SimpleNamespace(  # type: ignore[attr-defined]
            advisory_text="Detailed raw domain response.",
            domain_outcome="resolved",
        )

        reply = agent.escalate_to_domain_leader("Question", "proj-001", "trace-1")

        assert "Domain Leader review completed" in reply

    def test_escalate_to_dl_not_raw_dl_text(self) -> None:
        raw_text = "Detailed raw domain response."
        agent, _, _ = _make_agent()
        agent._domain_leader_agent = MagicMock()  # type: ignore[attr-defined]
        agent._domain_leader_agent.handle_escalation.return_value = SimpleNamespace(  # type: ignore[attr-defined]
            advisory_text=raw_text,
            domain_outcome="resolved",
        )

        reply = agent.escalate_to_domain_leader("Question", "proj-001", "trace-1")

        assert reply != raw_text


class TestPMAdminPath:
    def test_admin_rejects_without_ceo_approval_evidence(self, tmp_path: Path) -> None:
        agent, _, _ = _make_agent(
            artifact_repo=InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        )

        with pytest.raises(PMWriteNotAllowedError, match="ceo"):
            agent.handle(
                _request(
                    intent="ADMIN",
                    context={
                        "artifact_type": "scope_statement",
                        "content_md": "update",
                        "project_state": "active",
                        "approval_evidence": {"cwo_approval": True},
                    },
                )
            )

    def test_admin_rejects_without_cwo_approval_evidence(self, tmp_path: Path) -> None:
        agent, _, _ = _make_agent(
            artifact_repo=InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        )

        with pytest.raises(PMWriteNotAllowedError, match="cwo"):
            agent.handle(
                _request(
                    intent="ADMIN",
                    context={
                        "artifact_type": "scope_statement",
                        "content_md": "update",
                        "project_state": "active",
                        "approval_evidence": {"ceo_approval": True},
                    },
                )
            )

    def test_admin_succeeds_with_both_approval_evidences(self, tmp_path: Path) -> None:
        repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        agent, _, _ = _make_agent(artifact_repo=repo)

        response = agent.handle(
            _request(
                intent="ADMIN",
                context={
                    "artifact_type": "scope_statement",
                    "content_md": "approved update",
                    "project_state": "active",
                    "approval_evidence": {"ceo_approval": True, "cwo_approval": True},
                },
            )
        )

        artifact = repo.read_latest_artifact("proj-001", "scope_statement")
        assert response.artifact_updated is True
        assert artifact is not None
        assert artifact.content == "approved update"


class TestPMBudgetRiskEscalation:
    def test_budget_risk_escalation_emits_event_to_cwo_chain(self) -> None:
        repo = MagicMock()
        repo.write_escalation_event = MagicMock()
        runtime_repo = InMemoryRuntimeStateRepository()
        data_access = _make_data_access(runtime_repo=runtime_repo)
        agent = ProjectManagerAgent(
            llm_gateway=_make_llm("Decision: monitor budget risk."),
            artifact_writer=PMProjectArtifactWriter(
                project_artifact_repo=InMemoryProjectArtifactRepository()
            ),
            data_access=data_access,  # type: ignore[arg-type]
            domain_leader_agent=MagicMock(),
            task_dispatch_service=cast(Any, _DispatchServiceStub(runtime_repo)),
            project_artifact_repo=repo,
            trace_id_factory=lambda: "generated-trace",
        )

        agent._emit_budget_risk_escalation(
            "proj-001", "Budget consumption exceeded plan.", "trace-1"
        )

        repo.write_escalation_event.assert_called_once_with(
            project_id="proj-001",
            escalation_type="budget_risk",
            source="project_manager",
            target="cwo",
            trace_id="trace-1",
            reason="Budget consumption exceeded plan.",
            rule_ids=("ESC-004", "AUTH-002"),
        )
