"""Specialist agent implementation."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Callable

from openqilin.agents.specialist.models import (
    SpecialistDispatchAuthError,
    SpecialistRequest,
    SpecialistResponse,
    ToolNotAuthorizedError,
)
from openqilin.agents.specialist.task_executor import SpecialistTaskExecutor
from openqilin.data_access.repositories.artifacts import ProjectArtifactWriteContext
from openqilin.data_access.repositories.task_execution_results import (
    TaskExecutionResult,
    TaskExecutionResultsRepository,
)

if TYPE_CHECKING:
    from openqilin.agents.auditor.enforcement import AuditWriter
    from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
        PostgresGovernanceArtifactRepository,
    )

_SYSTEM_PROJECT_ID = "system"
_SPECIALIST_AGENT_ID = "specialist"

_AUDITOR_FINDING_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="auditor",
    project_status="active",
)


class SpecialistAgent:
    """Task execution worker dispatched exclusively by Project Manager."""

    def __init__(
        self,
        executor: SpecialistTaskExecutor,
        task_execution_results_repo: TaskExecutionResultsRepository,
        governance_repo: "PostgresGovernanceArtifactRepository",
        audit_writer: "AuditWriter",
        trace_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._executor = executor
        self._task_execution_results_repo = task_execution_results_repo
        self._governance_repo = governance_repo
        self._audit_writer = audit_writer
        self._trace_id_factory = trace_id_factory or (lambda: str(uuid.uuid4()))

    def handle(self, request: SpecialistRequest) -> SpecialistResponse:
        """Execute a PM-dispatched task."""

        normalized_source = request.dispatch_source_role.strip().lower()
        if normalized_source != "project_manager":
            raise SpecialistDispatchAuthError(
                "Specialist can only be dispatched by project_manager; "
                f"received dispatch_source_role={request.dispatch_source_role!r}"
            )

        task_id = request.task_id.strip()
        if not task_id:
            raise SpecialistDispatchAuthError("Specialist requires a non-empty task_id")

        clarification_question = _check_clarification_needed(request)
        if clarification_question is not None:
            return SpecialistResponse(
                execution_status="clarification_needed",
                output_text="Task paused — clarification required before execution.",
                artifact_id=None,
                blocker=f"clarification_needed: {clarification_question}",
                trace_id=request.trace_id,
            )

        tools_requested = _extract_tools_requested(request)

        try:
            output_text = self._executor.execute(
                task_description=request.task_description,
                approved_tools=request.approved_tools,
                tools_requested=tools_requested,
            )
        except ToolNotAuthorizedError as exc:
            return SpecialistResponse(
                execution_status="blocked",
                output_text=f"Task blocked: {exc}",
                artifact_id=None,
                blocker=f"tool_not_authorized: {exc.tool_name}",
                trace_id=request.trace_id,
            )

        result = self._task_execution_results_repo.write_result(
            TaskExecutionResult(
                result_id=self._trace_id_factory(),
                task_id=task_id,
                specialist_agent_id=_SPECIALIST_AGENT_ID,
                output_text=output_text,
                tools_used=tools_requested,
                execution_status="completed",
                trace_id=request.trace_id,
                created_at=datetime.now(tz=UTC),
            )
        )

        self._audit_writer.write_event(
            event_type="specialist_task_completed",
            outcome="completed",
            trace_id=request.trace_id,
            request_id=None,
            task_id=task_id,
            principal_id=_SPECIALIST_AGENT_ID,
            principal_role="specialist",
            source="specialist",
            reason_code="task_executed",
            message=f"task execution completed for task_id={task_id}",
            policy_version="v2",
            policy_hash="specialist-v1",
            rule_ids=["AUTH-001", "ORCH-006"],
            payload={"task_id": task_id, "project_id": request.project_id},
        )

        return SpecialistResponse(
            execution_status="completed",
            output_text=output_text,
            artifact_id=result.result_id,
            blocker=None,
            trace_id=request.trace_id,
        )

    def report_behavioral_violation(
        self,
        *,
        task_id: str,
        project_id: str,
        description: str,
        trace_id: str,
    ) -> str:
        """Emit a behavioral violation event on the specialist -> PM escalation path."""

        effective_trace_id = trace_id or self._trace_id_factory()

        self._audit_writer.write_event(
            event_type="behavioral_violation",
            outcome="escalated",
            trace_id=effective_trace_id,
            request_id=None,
            task_id=task_id,
            principal_id=_SPECIALIST_AGENT_ID,
            principal_role="specialist",
            source="specialist",
            reason_code="behavioral_violation",
            message=description,
            policy_version="v2",
            policy_hash="specialist-v1",
            rule_ids=["AUTH-001", "ORCH-006"],
            payload={
                "incident_type": "behavioral_violation",
                "current_owner_role": "specialist",
                "next_owner_role": "project_manager",
                "path_reference": "specialist -> project_manager -> auditor -> owner",
                "task_id": task_id,
                "project_id": project_id,
            },
        )

        pointer = self._governance_repo.write_project_artifact(
            project_id=_SYSTEM_PROJECT_ID,
            artifact_type="auditor_finding",
            content=json.dumps(
                {
                    "event_type": "behavioral_violation",
                    "incident_type": "behavioral_violation",
                    "severity": "high",
                    "current_owner_role": "specialist",
                    "next_owner_role": "project_manager",
                    "path_reference": "specialist -> project_manager -> auditor -> owner",
                    "rule_ids": ["AUTH-001", "ORCH-006"],
                    "task_id": task_id,
                    "project_id": project_id,
                    "description": description,
                    "trace_id": effective_trace_id,
                },
                sort_keys=True,
            ),
            write_context=_AUDITOR_FINDING_WRITE_CONTEXT,
        )
        return pointer.storage_uri


def _check_clarification_needed(request: SpecialistRequest) -> str | None:
    """Return clarification question if DL clarification is needed, else None."""

    marker = "[clarification_needed:"
    idx = request.task_description.find(marker)
    if idx == -1:
        return None
    start = idx + len(marker)
    end = request.task_description.find("]", start)
    if end == -1:
        return request.task_description[start:].strip()
    return request.task_description[start:end].strip()


def _extract_tools_requested(request: SpecialistRequest) -> tuple[str, ...]:
    """Extract tool names from task_description context."""

    marker = "[tools:"
    idx = request.task_description.find(marker)
    if idx == -1:
        return ()
    start = idx + len(marker)
    end = request.task_description.find("]", start)
    if end == -1:
        raw = request.task_description[start:].strip()
    else:
        raw = request.task_description[start:end].strip()
    return tuple(tool.strip() for tool in raw.split(",") if tool.strip())
