"""Governed intent-level write-action tools for runtime/project mutations."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from typing import Mapping
from uuid import uuid4

from openqilin.budget_runtime.client import InMemoryBudgetRuntimeClient
from openqilin.budget_runtime.models import BudgetReservationInput
from openqilin.control_plane.handlers.governance_handler import (
    GovernanceHandlerError,
    archive_project_by_governance,
    finalize_project_completion_by_c_suite,
    pause_project_by_governance,
    resume_project_by_governance,
    terminate_project_by_governance,
)
from openqilin.data_access.repositories.artifacts import (
    InMemoryProjectArtifactRepository,
    ProjectArtifactRepositoryError,
    ProjectArtifactWriteContext,
)
from openqilin.data_access.repositories.governance import (
    InMemoryGovernanceRepository,
    ProjectRecord,
)
from openqilin.execution_sandbox.tools.access_policy import is_write_tool_allowed
from openqilin.execution_sandbox.tools.contracts import (
    ToolCallContext,
    ToolResult,
    ToolSourceDescriptor,
)
from openqilin.observability.audit.audit_writer import InMemoryAuditWriter

_WRITE_TOOL_COST_UNITS: Mapping[str, int] = {
    "transition_project_lifecycle": 40,
    "append_decision_log": 15,
    "append_progress_report": 20,
    "upsert_project_artifact": 25,
}


class GovernedWriteToolService:
    """Intent-level write tool runtime with fail-closed governance controls."""

    def __init__(
        self,
        *,
        governance_repository: InMemoryGovernanceRepository,
        project_artifact_repository: InMemoryProjectArtifactRepository,
        audit_writer: InMemoryAuditWriter,
        budget_runtime_client: InMemoryBudgetRuntimeClient | None = None,
    ) -> None:
        self._governance_repository = governance_repository
        self._project_artifact_repository = project_artifact_repository
        self._audit_writer = audit_writer
        self._budget_runtime_client = budget_runtime_client
        self._idempotent_results: dict[str, ToolResult] = {}

    def call_tool(
        self,
        *,
        tool_name: str,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        """Invoke one governed mutation tool with role/lifecycle guards."""

        normalized_tool = tool_name.strip().lower()
        if not normalized_tool:
            result = self._deny(
                tool_name=tool_name,
                context=context,
                code="tool_name_missing",
                message="tool_name is required",
            )
            self._audit_write_attempt(result=result, context=context)
            return result
        if any(marker in normalized_tool for marker in ("raw", "sql", "db_")):
            result = self._deny(
                tool_name=normalized_tool,
                context=context,
                code="tool_raw_db_mutation_denied",
                message="raw or direct DB mutation tools are forbidden; use intent-level tools",
            )
            self._audit_write_attempt(result=result, context=context)
            return result
        if not is_write_tool_allowed(role=context.principal_role, tool_name=normalized_tool):
            result = self._deny(
                tool_name=normalized_tool,
                context=context,
                code="tool_access_denied",
                message="write tool is not allowed for recipient role",
            )
            self._audit_write_attempt(result=result, context=context)
            return result

        idempotency_key = self._idempotency_key(
            request_id=context.request_id,
            tool_name=normalized_tool,
            arguments=arguments,
        )
        replayed = self._idempotent_results.get(idempotency_key)
        if replayed is not None:
            replayed_data = dict(replayed.data or {})
            replayed_data["replayed"] = True
            result = ToolResult(
                decision=replayed.decision,
                tool_name=replayed.tool_name,
                tool_call_id=replayed.tool_call_id,
                trace_id=replayed.trace_id,
                request_id=replayed.request_id,
                data=replayed_data,
                sources=replayed.sources,
                error_code=replayed.error_code,
                message=replayed.message,
            )
            self._audit_write_attempt(result=result, context=context)
            return result

        budget_result = self._reserve_budget_if_configured(
            tool_name=normalized_tool,
            arguments=arguments,
            context=context,
        )
        if budget_result is not None:
            self._audit_write_attempt(result=budget_result, context=context)
            self._idempotent_results[idempotency_key] = budget_result
            return budget_result

        handler = getattr(self, f"_tool_{normalized_tool}", None)
        if handler is None:
            result = self._deny(
                tool_name=normalized_tool,
                context=context,
                code="tool_unknown",
                message="unknown write tool",
            )
            self._audit_write_attempt(result=result, context=context)
            self._idempotent_results[idempotency_key] = result
            return result
        try:
            result = handler(arguments=arguments, context=context)
        except Exception as error:
            result = self._deny(
                tool_name=normalized_tool,
                context=context,
                code="tool_runtime_error",
                message=f"tool execution failed: {error}",
            )
        self._audit_write_attempt(result=result, context=context)
        self._idempotent_results[idempotency_key] = result
        return result

    def _tool_transition_project_lifecycle(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        project_id, project, project_error = self._resolve_project(
            arguments=arguments, context=context
        )
        if project_error is not None or project is None:
            return project_error or self._deny(
                tool_name="transition_project_lifecycle",
                context=context,
                code="tool_project_missing",
                message=f"project not found: {project_id}",
            )
        previous_status = project.status

        next_status = str(arguments.get("next_status") or "").strip().lower()
        if not next_status:
            return self._deny(
                tool_name="transition_project_lifecycle",
                context=context,
                code="tool_next_status_missing",
                message="next_status is required",
            )
        reason_code = (
            str(arguments.get("reason_code") or "tool_mutation").strip() or "tool_mutation"
        )

        try:
            if next_status == "paused":
                lifecycle_outcome = pause_project_by_governance(
                    repository=self._governance_repository,
                    project_id=project_id,
                    actor_role=context.recipient_role,
                    trace_id=context.trace_id,
                    reason_code=reason_code,
                )
            elif next_status == "active":
                lifecycle_outcome = resume_project_by_governance(
                    repository=self._governance_repository,
                    project_id=project_id,
                    actor_role=context.recipient_role,
                    trace_id=context.trace_id,
                    reason_code=reason_code,
                )
            elif next_status == "terminated":
                lifecycle_outcome = terminate_project_by_governance(
                    repository=self._governance_repository,
                    project_id=project_id,
                    actor_role=context.recipient_role,
                    trace_id=context.trace_id,
                    reason_code=reason_code,
                )
            elif next_status == "archived":
                lifecycle_outcome = archive_project_by_governance(
                    repository=self._governance_repository,
                    project_id=project_id,
                    actor_role=context.recipient_role,
                    trace_id=context.trace_id,
                    reason_code=reason_code,
                )
            elif next_status == "completed":
                outcome = finalize_project_completion_by_c_suite(
                    repository=self._governance_repository,
                    project_id=project_id,
                    actor_role=context.recipient_role,
                    trace_id=context.trace_id,
                    reason_code=reason_code,
                )
                data = {
                    "project_id": outcome.project.project_id,
                    "previous_status": previous_status,
                    "current_status": outcome.project.status,
                    "reason_code": reason_code,
                }
                return self._ok(
                    tool_name="transition_project_lifecycle",
                    context=context,
                    data=data,
                    sources=(
                        ToolSourceDescriptor(
                            source_id=f"project:{outcome.project.project_id}",
                            source_kind="project_record",
                            version=f"status:{outcome.project.status}",
                            updated_at=outcome.project.updated_at.isoformat(),
                        ),
                    ),
                )
            else:
                return self._deny(
                    tool_name="transition_project_lifecycle",
                    context=context,
                    code="tool_next_status_invalid",
                    message=f"unsupported next_status: {next_status}",
                )
        except GovernanceHandlerError as error:
            return self._deny(
                tool_name="transition_project_lifecycle",
                context=context,
                code=error.code,
                message=error.message,
            )

        data = {
            "project_id": lifecycle_outcome.project.project_id,
            "previous_status": previous_status,
            "current_status": lifecycle_outcome.project.status,
            "reason_code": reason_code,
        }
        return self._ok(
            tool_name="transition_project_lifecycle",
            context=context,
            data=data,
            sources=(
                ToolSourceDescriptor(
                    source_id=f"project:{lifecycle_outcome.project.project_id}",
                    source_kind="project_record",
                    version=f"status:{lifecycle_outcome.project.status}",
                    updated_at=lifecycle_outcome.project.updated_at.isoformat(),
                ),
            ),
        )

    def _tool_append_decision_log(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        return self._write_project_artifact(
            tool_name="append_decision_log",
            artifact_type="decision_log",
            arguments=arguments,
            context=context,
        )

    def _tool_append_progress_report(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        return self._write_project_artifact(
            tool_name="append_progress_report",
            artifact_type="progress_report",
            arguments=arguments,
            context=context,
        )

    def _tool_upsert_project_artifact(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        artifact_type = str(arguments.get("artifact_type") or "").strip().lower()
        if not artifact_type:
            return self._deny(
                tool_name="upsert_project_artifact",
                context=context,
                code="tool_artifact_type_missing",
                message="artifact_type is required",
            )
        return self._write_project_artifact(
            tool_name="upsert_project_artifact",
            artifact_type=artifact_type,
            arguments=arguments,
            context=context,
        )

    def _write_project_artifact(
        self,
        *,
        tool_name: str,
        artifact_type: str,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        project_id, project, project_error = self._resolve_project(
            arguments=arguments, context=context
        )
        if project_error is not None or project is None:
            return project_error or self._deny(
                tool_name=tool_name,
                context=context,
                code="tool_project_missing",
                message=f"project not found: {project_id}",
            )
        content = str(arguments.get("content") or "").strip()
        if not content:
            return self._deny(
                tool_name=tool_name,
                context=context,
                code="tool_content_missing",
                message="content is required",
            )
        approval_roles = _normalize_roles(arguments.get("approval_roles"))
        try:
            pointer = self._project_artifact_repository.write_project_artifact(
                project_id=project_id,
                artifact_type=artifact_type,
                content=content,
                write_context=ProjectArtifactWriteContext(
                    actor_role=context.recipient_role,
                    project_status=project.status,
                    approval_roles=approval_roles,
                ),
            )
        except ProjectArtifactRepositoryError as error:
            return self._deny(
                tool_name=tool_name,
                context=context,
                code=error.code,
                message=error.message,
            )
        data = {
            "project_id": pointer.project_id,
            "artifact_type": pointer.artifact_type,
            "revision_no": pointer.revision_no,
            "storage_uri": pointer.storage_uri,
            "content_hash": pointer.content_hash,
            "byte_size": pointer.byte_size,
        }
        return self._ok(
            tool_name=tool_name,
            context=context,
            data=data,
            sources=(
                ToolSourceDescriptor(
                    source_id=f"artifact:{pointer.artifact_type}",
                    source_kind="artifact",
                    version=f"v{pointer.revision_no}",
                    updated_at=pointer.created_at.isoformat(),
                ),
            ),
        )

    def _reserve_budget_if_configured(
        self,
        *,
        tool_name: str,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> ToolResult | None:
        if self._budget_runtime_client is None:
            return None
        estimated_cost_units = _WRITE_TOOL_COST_UNITS.get(tool_name, 25)
        reservation = self._budget_runtime_client.reserve(
            BudgetReservationInput(
                task_id=context.task_id,
                request_id=context.request_id,
                trace_id=context.trace_id,
                principal_id=context.principal_id,
                command=f"tool_write:{tool_name}",
                args=(json.dumps(arguments, sort_keys=True, ensure_ascii=True),),
                estimated_cost_units=estimated_cost_units,
            )
        )
        if reservation.decision == "allow":
            return None
        if reservation.decision == "deny":
            return self._deny(
                tool_name=tool_name,
                context=context,
                code=reservation.reason_code,
                message=reservation.reason_message,
            )
        return self._deny(
            tool_name=tool_name,
            context=context,
            code="budget_uncertain_fail_closed",
            message="budget decision uncertain; write tool denied fail-closed",
        )

    def _resolve_project(
        self,
        *,
        arguments: Mapping[str, object],
        context: ToolCallContext,
    ) -> tuple[str, ProjectRecord | None, ToolResult | None]:
        requested_project = (
            str(arguments.get("project_id") or "").strip() or context.project_id or ""
        )
        if not requested_project:
            return (
                "",
                None,
                self._deny(
                    tool_name=str(arguments.get("tool_name") or "tool"),
                    context=context,
                    code="tool_project_scope_required",
                    message="project_id is required",
                ),
            )
        if context.project_id is not None and requested_project != context.project_id:
            return (
                requested_project,
                None,
                self._deny(
                    tool_name=str(arguments.get("tool_name") or "tool"),
                    context=context,
                    code="tool_project_scope_mismatch",
                    message="requested project_id differs from command scope",
                ),
            )
        project = self._governance_repository.get_project(requested_project)
        if project is None:
            return (
                requested_project,
                None,
                self._deny(
                    tool_name=str(arguments.get("tool_name") or "tool"),
                    context=context,
                    code="tool_project_missing",
                    message=f"project not found: {requested_project}",
                ),
            )
        return requested_project, project, None

    def _audit_write_attempt(self, *, result: ToolResult, context: ToolCallContext) -> None:
        self._audit_writer.write_event(
            event_type=f"tool.write.{result.tool_name}",
            outcome=result.decision,
            trace_id=context.trace_id,
            request_id=context.request_id,
            task_id=context.task_id,
            principal_id=context.principal_id,
            principal_role=context.principal_role,
            source="tool_orchestration",
            reason_code=result.error_code,
            message=result.message,
            payload={
                "tool_name": result.tool_name,
                "decision": result.decision,
                "data": json.dumps(result.data or {}, sort_keys=True, ensure_ascii=True)[:4000],
                "source_count": len(result.sources),
            },
            attributes={
                "tool_name": result.tool_name,
                "decision": result.decision,
            },
        )

    @staticmethod
    def _idempotency_key(
        *,
        request_id: str,
        tool_name: str,
        arguments: Mapping[str, object],
    ) -> str:
        payload = json.dumps(arguments, sort_keys=True, ensure_ascii=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"{request_id}::{tool_name}::{digest}"

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
    def summarize_for_response(result: ToolResult) -> str:
        """Serialize write-tool result into deterministic response text."""

        payload = {
            "tool_name": result.tool_name,
            "decision": result.decision,
            "data": result.data,
            "sources": [asdict(source) for source in result.sources],
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=True)[:1500]


def _normalize_roles(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        tokens = [item.strip().lower() for item in value.split(",") if item.strip()]
        return tuple(tokens)
    if isinstance(value, list):
        tokens = [str(item).strip().lower() for item in value if str(item).strip()]
        return tuple(tokens)
    return ()
