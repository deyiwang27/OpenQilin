"""Governed intent-level read tools for grounded factual responses."""

from __future__ import annotations

from dataclasses import asdict
import json
from typing import Mapping
from uuid import uuid4

from openqilin.control_plane.governance.project_lifecycle import allowed_project_status_transitions
from openqilin.data_access.repositories.artifacts import ProjectArtifactRepositoryError
from openqilin.data_access.repositories.communication import CommunicationDeadLetterRecord
from openqilin.data_access.repositories.governance import ProjectRecord
from openqilin.data_access.repositories.postgres.communication_repository import (
    PostgresCommunicationRepository,
)
from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
    PostgresGovernanceArtifactRepository,
)
from openqilin.data_access.repositories.postgres.project_repository import PostgresProjectRepository
from openqilin.data_access.repositories.postgres.task_repository import PostgresTaskRepository
from openqilin.execution_sandbox.tools.access_policy import is_read_tool_allowed
from openqilin.execution_sandbox.tools.contracts import (
    ToolCallContext,
    ToolResult,
    ToolSourceDescriptor,
)
from openqilin.observability.audit.audit_writer import OTelAuditWriter
from openqilin.observability.testing.stubs import InMemoryAuditWriter
from openqilin.retrieval_runtime.models import RetrievalQueryRequest
from openqilin.retrieval_runtime.service import RetrievalQueryService


class GovernedReadToolService:
    """Intent-level read tool runtime with role/scope fail-closed checks."""

    def __init__(
        self,
        *,
        governance_repository: PostgresProjectRepository,
        project_artifact_repository: PostgresGovernanceArtifactRepository,
        runtime_state_repository: PostgresTaskRepository,
        retrieval_query_service: RetrievalQueryService,
        audit_writer: InMemoryAuditWriter | OTelAuditWriter,
        communication_repository: PostgresCommunicationRepository | None = None,
    ) -> None:
        self._governance_repository = governance_repository
        self._project_artifact_repository = project_artifact_repository
        self._runtime_state_repository = runtime_state_repository
        self._retrieval_query_service = retrieval_query_service
        self._audit_writer = audit_writer
        self._communication_repository = communication_repository

    def call_tool(
        self,
        *,
        tool_name: str,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        """Invoke one read tool with governed access controls."""

        normalized_tool = tool_name.strip().lower()
        if not normalized_tool:
            return self._deny(
                tool_name=tool_name,
                context=context,
                code="tool_name_missing",
                message="tool_name is required",
            )
        if not is_read_tool_allowed(role=context.recipient_role, tool_name=normalized_tool):
            return self._deny(
                tool_name=normalized_tool,
                context=context,
                code="tool_access_denied",
                message="read tool is not allowed for recipient role",
            )

        handler = getattr(self, f"_tool_{normalized_tool}", None)
        if handler is None:
            return self._deny(
                tool_name=normalized_tool,
                context=context,
                code="tool_unknown",
                message="unknown read tool",
            )
        try:
            return handler(arguments=arguments, context=context)
        except Exception as error:
            return self._deny(
                tool_name=normalized_tool,
                context=context,
                code="tool_runtime_error",
                message=f"tool execution failed: {error}",
            )

    def _tool_get_project_lifecycle_state(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        project = self._resolve_project(arguments=arguments, context=context)
        if isinstance(project, ToolResult):
            return project

        next_states = allowed_project_status_transitions(project.status)
        data = {
            "project_id": project.project_id,
            "status": project.status,
            "next_transitions": list(next_states),
            "updated_at": project.updated_at.isoformat(),
        }
        return self._ok(
            tool_name="get_project_lifecycle_state",
            context=context,
            data=data,
            sources=(
                ToolSourceDescriptor(
                    source_id=f"project:{project.project_id}",
                    source_kind="project_record",
                    version=f"status:{project.status}",
                    updated_at=project.updated_at.isoformat(),
                ),
            ),
        )

    def _tool_get_project_budget_snapshot(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        project = self._resolve_project(arguments=arguments, context=context)
        if isinstance(project, ToolResult):
            return project

        initialization = project.initialization
        budget_currency_total = initialization.budget_currency_total if initialization else 0.0
        budget_quota_total = initialization.budget_quota_total if initialization else 0.0
        used_currency = 0.0
        used_quota = 0.0
        remaining_currency = max(0.0, budget_currency_total - used_currency)
        remaining_quota = max(0.0, budget_quota_total - used_quota)
        data = {
            "project_id": project.project_id,
            "currency_total": round(budget_currency_total, 6),
            "currency_used": round(used_currency, 6),
            "currency_remaining": round(remaining_currency, 6),
            "quota_total": round(budget_quota_total, 6),
            "quota_used": round(used_quota, 6),
            "quota_remaining": round(remaining_quota, 6),
            "usage_source": "runtime_budget_usage_not_persisted",
            "baseline_initialized": initialization is not None,
        }
        return self._ok(
            tool_name="get_project_budget_snapshot",
            context=context,
            data=data,
            sources=(
                ToolSourceDescriptor(
                    source_id=f"project:{project.project_id}",
                    source_kind="budget",
                    version="initialization_snapshot",
                    updated_at=project.updated_at.isoformat(),
                ),
            ),
        )

    def _tool_get_project_milestone_status(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        project = self._resolve_project(arguments=arguments, context=context)
        if isinstance(project, ToolResult):
            return project

        execution_plan = self._project_artifact_repository.read_latest_artifact(
            project_id=project.project_id,
            artifact_type="execution_plan",
        )
        progress_report = self._project_artifact_repository.read_latest_artifact(
            project_id=project.project_id,
            artifact_type="progress_report",
        )
        milestone_lines: tuple[str, ...] = ()
        if execution_plan is not None:
            lines = tuple(
                line.strip()
                for line in execution_plan.content.splitlines()
                if line.strip().startswith(("-", "*", "1.", "2.", "3.", "4.", "5."))
            )
            milestone_lines = lines[:12]

        data = {
            "project_id": project.project_id,
            "milestones_total": len(milestone_lines),
            "completion_percent": 0 if len(milestone_lines) == 0 else 20,
            "blocked_milestones": [],
            "due_date_risk_flags": [],
            "latest_execution_plan_revision": (
                execution_plan.pointer.revision_no if execution_plan is not None else None
            ),
            "latest_progress_report_revision": (
                progress_report.pointer.revision_no if progress_report is not None else None
            ),
        }
        sources: list[ToolSourceDescriptor] = [
            ToolSourceDescriptor(
                source_id=f"project:{project.project_id}",
                source_kind="project_record",
                version=f"status:{project.status}",
                updated_at=project.updated_at.isoformat(),
            )
        ]
        if execution_plan is not None:
            sources.append(
                ToolSourceDescriptor(
                    source_id=f"artifact:{execution_plan.pointer.artifact_type}",
                    source_kind="artifact",
                    version=f"v{execution_plan.pointer.revision_no}",
                    updated_at=execution_plan.pointer.created_at.isoformat(),
                )
            )
        if progress_report is not None:
            sources.append(
                ToolSourceDescriptor(
                    source_id=f"artifact:{progress_report.pointer.artifact_type}",
                    source_kind="artifact",
                    version=f"v{progress_report.pointer.revision_no}",
                    updated_at=progress_report.pointer.created_at.isoformat(),
                )
            )
        return self._ok(
            tool_name="get_project_milestone_status",
            context=context,
            data=data,
            sources=tuple(sources),
        )

    def _tool_get_project_task_board(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        project_id = self._resolve_project_scope(arguments=arguments, context=context)
        if isinstance(project_id, ToolResult):
            return project_id

        limit = _normalize_int(arguments.get("limit"), default=20, minimum=1, maximum=100)
        raw_filter = str(arguments.get("status_filter") or "").strip().lower()
        status_filter = {value.strip() for value in raw_filter.split(",") if value.strip()}
        tasks = tuple(
            task
            for task in self._runtime_state_repository.list_tasks()
            if task.project_id == project_id
            and (len(status_filter) == 0 or task.status in status_filter)
        )
        ordered = tuple(
            sorted(tasks, key=lambda task: (task.created_at, task.task_id), reverse=True)
        )
        top = ordered[:limit]
        data = {
            "project_id": project_id,
            "result_count": len(top),
            "tasks": [
                {
                    "task_id": task.task_id,
                    "status": task.status,
                    "command": task.command,
                    "target": task.target,
                    "dispatch_target": task.dispatch_target,
                    "outcome_error_code": task.outcome_error_code,
                    "created_at": task.created_at.isoformat(),
                }
                for task in top
            ],
        }
        updated_at = top[0].created_at.isoformat() if len(top) > 0 else None
        return self._ok(
            tool_name="get_project_task_board",
            context=context,
            data=data,
            sources=(
                ToolSourceDescriptor(
                    source_id=f"runtime:tasks:{project_id}",
                    source_kind="task",
                    version=f"count:{len(tasks)}",
                    updated_at=updated_at,
                ),
            ),
        )

    def _tool_search_project_docs(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        project_id = self._resolve_project_scope(arguments=arguments, context=context)
        if isinstance(project_id, ToolResult):
            return project_id

        query = str(arguments.get("query") or "").strip()
        if not query:
            return self._deny(
                tool_name="search_project_docs",
                context=context,
                code="tool_query_missing",
                message="query is required",
            )
        limit = _normalize_int(arguments.get("limit"), default=5, minimum=1, maximum=20)
        artifact_type = str(arguments.get("artifact_type") or "").strip().lower() or None
        retrieval = self._retrieval_query_service.search_project_artifacts(
            RetrievalQueryRequest(
                project_id=project_id,
                query=query,
                limit=limit,
                artifact_type=artifact_type,
            )
        )
        if retrieval.decision != "ok":
            return self._deny(
                tool_name="search_project_docs",
                context=context,
                code=retrieval.error_code or "retrieval_query_denied",
                message=retrieval.message,
            )

        hits = [
            {
                "artifact_id": hit.artifact_id,
                "artifact_type": hit.artifact_type,
                "title": hit.title,
                "snippet": hit.snippet,
                "source_ref": hit.source_ref,
                "score": hit.score,
            }
            for hit in retrieval.hits
        ]
        sources = tuple(
            ToolSourceDescriptor(
                source_id=f"artifact:{hit.artifact_id}",
                source_kind="artifact",
                version=f"score:{hit.score}",
                updated_at=None,
            )
            for hit in retrieval.hits
        )
        return self._ok(
            tool_name="search_project_docs",
            context=context,
            data={
                "project_id": project_id,
                "query": query,
                "result_count": len(hits),
                "hits": hits,
            },
            sources=sources,
        )

    def _tool_get_project_doc_latest(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        project_id = self._resolve_project_scope(arguments=arguments, context=context)
        if isinstance(project_id, ToolResult):
            return project_id

        artifact_type = str(arguments.get("artifact_type") or "").strip().lower()
        if not artifact_type:
            return self._deny(
                tool_name="get_project_doc_latest",
                context=context,
                code="tool_artifact_type_missing",
                message="artifact_type is required",
            )
        try:
            document = self._project_artifact_repository.read_latest_artifact(
                project_id=project_id,
                artifact_type=artifact_type,
            )
        except ProjectArtifactRepositoryError as error:
            return self._deny(
                tool_name="get_project_doc_latest",
                context=context,
                code=error.code,
                message=error.message,
            )
        if document is None:
            return self._deny(
                tool_name="get_project_doc_latest",
                context=context,
                code="tool_artifact_missing",
                message="artifact not found",
            )
        excerpt = document.content.strip().replace("\n", " ")
        data = {
            "project_id": project_id,
            "artifact_type": artifact_type,
            "revision_no": document.pointer.revision_no,
            "storage_uri": document.pointer.storage_uri,
            "content_hash": document.pointer.content_hash,
            "excerpt": excerpt[:500],
        }
        return self._ok(
            tool_name="get_project_doc_latest",
            context=context,
            data=data,
            sources=(
                ToolSourceDescriptor(
                    source_id=f"artifact:{artifact_type}",
                    source_kind="artifact",
                    version=f"v{document.pointer.revision_no}",
                    updated_at=document.pointer.created_at.isoformat(),
                ),
            ),
        )

    def _tool_get_completion_gate_status(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        project = self._resolve_project(arguments=arguments, context=context)
        if isinstance(project, ToolResult):
            return project

        report_present = project.completion_report is not None
        approval_roles = {item.actor_role for item in project.completion_approvals}
        required_roles = {"ceo", "cwo"}
        missing_roles = tuple(sorted(required_roles - approval_roles))
        owner_notified = project.completion_owner_notified_at is not None
        data = {
            "project_id": project.project_id,
            "report_present": report_present,
            "approval_roles": sorted(approval_roles),
            "missing_approval_roles": list(missing_roles),
            "owner_notified": owner_notified,
            "ready_for_completion_transition": report_present
            and len(missing_roles) == 0
            and owner_notified,
        }
        return self._ok(
            tool_name="get_completion_gate_status",
            context=context,
            data=data,
            sources=(
                ToolSourceDescriptor(
                    source_id=f"project:{project.project_id}",
                    source_kind="project_record",
                    version=f"status:{project.status}",
                    updated_at=project.updated_at.isoformat(),
                ),
            ),
        )

    def _tool_get_project_workforce_snapshot(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        project = self._resolve_project(arguments=arguments, context=context)
        if isinstance(project, ToolResult):
            return project

        bindings = [
            {
                "role": binding.role,
                "template_id": binding.template_id,
                "binding_status": binding.binding_status,
                "llm_routing_profile": binding.llm_routing_profile,
                "mandatory_operations": list(binding.mandatory_operations),
                "created_at": binding.created_at.isoformat(),
            }
            for binding in project.workforce_bindings
        ]
        data = {
            "project_id": project.project_id,
            "binding_count": len(bindings),
            "bindings": bindings,
        }
        return self._ok(
            tool_name="get_project_workforce_snapshot",
            context=context,
            data=data,
            sources=(
                ToolSourceDescriptor(
                    source_id=f"project:{project.project_id}",
                    source_kind="project_record",
                    version=f"workforce_bindings:{len(bindings)}",
                    updated_at=project.updated_at.isoformat(),
                ),
            ),
        )

    def _tool_get_audit_event_stream(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        project_id = self._resolve_project_scope(arguments=arguments, context=context)
        if isinstance(project_id, ToolResult):
            return project_id

        task_ids = {
            task.task_id
            for task in self._runtime_state_repository.list_tasks()
            if task.project_id == project_id
        }
        limit = _normalize_int(arguments.get("limit"), default=20, minimum=1, maximum=100)
        raw_types = str(arguments.get("event_types") or "").strip().lower()
        event_types = {value.strip() for value in raw_types.split(",") if value.strip()}
        all_audit_events = (
            self._audit_writer.get_events()
            if isinstance(self._audit_writer, InMemoryAuditWriter)
            else ()
        )
        matched = [
            event
            for event in all_audit_events
            if (event.task_id in task_ids if event.task_id is not None else False)
            and (len(event_types) == 0 or event.event_type in event_types)
        ]
        matched.sort(key=lambda event: event.timestamp, reverse=True)
        top = matched[:limit]
        data = {
            "project_id": project_id,
            "result_count": len(top),
            "events": [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "outcome": event.outcome,
                    "task_id": event.task_id,
                    "trace_id": event.trace_id,
                    "actor_role": event.actor_role,
                    "source": event.source,
                    "reason_code": event.reason_code,
                    "message": event.message,
                    "timestamp": event.timestamp.isoformat(),
                }
                for event in top
            ],
        }
        updated_at = top[0].timestamp.isoformat() if len(top) > 0 else None
        return self._ok(
            tool_name="get_audit_event_stream",
            context=context,
            data=data,
            sources=(
                ToolSourceDescriptor(
                    source_id=f"audit:project:{project_id}",
                    source_kind="audit",
                    version=f"count:{len(matched)}",
                    updated_at=updated_at,
                ),
            ),
        )

    def _tool_get_dispatch_denial_evidence(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        raw_task_id = str(arguments.get("task_id") or "").strip()
        if not raw_task_id:
            return self._deny(
                tool_name="get_dispatch_denial_evidence",
                context=context,
                code="tool_task_id_missing",
                message="task_id is required",
            )
        task = self._runtime_state_repository.get_task_by_id(raw_task_id)
        if task is None:
            return self._deny(
                tool_name="get_dispatch_denial_evidence",
                context=context,
                code="tool_task_missing",
                message="task not found",
            )
        if context.project_id is not None and task.project_id != context.project_id:
            return self._deny(
                tool_name="get_dispatch_denial_evidence",
                context=context,
                code="tool_project_scope_mismatch",
                message="task is outside project scope",
            )
        if task.status != "blocked":
            return self._deny(
                tool_name="get_dispatch_denial_evidence",
                context=context,
                code="tool_task_not_denied",
                message="task is not a denied/blocked dispatch",
            )

        dead_letters: tuple[CommunicationDeadLetterRecord, ...] = ()
        if self._communication_repository is not None:
            all_dead_letters = self._communication_repository.list_dead_letter_records()
            dead_letters = tuple(r for r in all_dead_letters if r.task_id == task.task_id)
        data = {
            "task_id": task.task_id,
            "status": task.status,
            "project_id": task.project_id,
            "dispatch_target": task.dispatch_target,
            "outcome_source": task.outcome_source,
            "error_code": task.outcome_error_code,
            "message": task.outcome_message,
            "dead_letters": [
                {
                    "dead_letter_id": record.dead_letter_id,
                    "error_code": record.error_code,
                    "error_message": record.error_message,
                    "attempts": record.attempts,
                    "created_at": record.created_at.isoformat(),
                }
                for record in dead_letters
            ],
        }
        sources = [
            ToolSourceDescriptor(
                source_id=f"task:{task.task_id}",
                source_kind="task",
                version=f"status:{task.status}",
                updated_at=task.created_at.isoformat(),
            )
        ]
        for record in dead_letters:
            sources.append(
                ToolSourceDescriptor(
                    source_id=f"dead_letter:{record.dead_letter_id}",
                    source_kind="runtime",
                    version=f"attempts:{record.attempts}",
                    updated_at=record.created_at.isoformat(),
                )
            )
        return self._ok(
            tool_name="get_dispatch_denial_evidence",
            context=context,
            data=data,
            sources=tuple(sources),
        )

    def _resolve_project_scope(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> str | ToolResult:
        requested = str(arguments.get("project_id") or "").strip() or context.project_id or ""
        if not requested:
            return self._deny(
                tool_name=str(arguments.get("tool_name") or "tool"),
                context=context,
                code="tool_project_scope_required",
                message="project_id is required",
            )
        if context.project_id is not None and requested != context.project_id:
            return self._deny(
                tool_name=str(arguments.get("tool_name") or "tool"),
                context=context,
                code="tool_project_scope_mismatch",
                message="requested project_id differs from command scope",
            )
        return requested

    def _resolve_project(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ProjectRecord | ToolResult:
        project_id = self._resolve_project_scope(arguments=arguments, context=context)
        if isinstance(project_id, ToolResult):
            return project_id
        project = self._governance_repository.get_project(project_id)
        if project is None:
            return self._deny(
                tool_name=str(arguments.get("tool_name") or "tool"),
                context=context,
                code="tool_project_missing",
                message=f"project not found: {project_id}",
            )
        return project

    def _ok(
        self,
        *,
        tool_name: str,
        context: ToolCallContext,
        data: Mapping[str, object],
        sources: tuple[ToolSourceDescriptor, ...],
    ) -> ToolResult:
        return ToolResult(
            decision="ok",
            tool_name=tool_name,
            tool_call_id=f"tool-{uuid4()}",
            trace_id=context.trace_id,
            request_id=context.request_id,
            data=data,
            sources=sources,
            error_code=None,
            message="ok",
        )

    def _deny(
        self,
        *,
        tool_name: str,
        context: ToolCallContext,
        code: str,
        message: str,
    ) -> ToolResult:
        return ToolResult(
            decision="denied",
            tool_name=tool_name,
            tool_call_id=f"tool-{uuid4()}",
            trace_id=context.trace_id,
            request_id=context.request_id,
            data=None,
            sources=(),
            error_code=code,
            message=message,
        )

    @staticmethod
    def summarize_for_grounding(result: ToolResult) -> str:
        """Serialize tool result data into compact grounding summary text."""

        payload = {
            "tool_name": result.tool_name,
            "decision": result.decision,
            "data": result.data,
            "sources": [asdict(source) for source in result.sources],
        }
        text = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return text[:1200]


def _normalize_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(str(value))
    except (ValueError, TypeError):
        parsed = default
    if parsed < minimum:
        return minimum
    if parsed > maximum:
        return maximum
    return parsed
