"""Enforcement helpers for the auditor agent."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Iterable, Protocol

from openqilin.agents.auditor.models import AuditorFindingError
from openqilin.communication_gateway.delivery.publisher import PublishRequest
from openqilin.data_access.repositories.artifacts import ProjectArtifactWriteContext
from openqilin.data_access.repositories.postgres.communication_repository import (
    PostgresCommunicationRepository,
)
from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
    PostgresGovernanceArtifactRepository,
)
from openqilin.task_orchestrator.services.lifecycle_service import TaskLifecycleService

_AUDITOR_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="auditor",
    project_status="active",
)


class AuditWriter(Protocol):
    """Protocol shared by the production and in-memory audit writers."""

    def write_event(
        self,
        *,
        event_type: str,
        outcome: str,
        trace_id: str,
        request_id: str | None,
        task_id: str | None,
        principal_id: str | None,
        principal_role: str | None = None,
        source: str,
        reason_code: str | None,
        message: str,
        policy_version: str | None = None,
        policy_hash: str | None = None,
        rule_ids: Iterable[str] | None = None,
        payload: dict[str, object] | None = None,
        attributes: dict[str, object] | None = None,
    ) -> object: ...


class AuditorEnforcementService:
    """Executes append-only enforcement actions for governance breaches."""

    def __init__(
        self,
        lifecycle_service: TaskLifecycleService,
        governance_repo: PostgresGovernanceArtifactRepository,
        audit_writer: AuditWriter,
        communication_repo: PostgresCommunicationRepository,
    ) -> None:
        self._lifecycle_service = lifecycle_service
        self._governance_repo = governance_repo
        self._audit_writer = audit_writer
        self._communication_repo = communication_repo

    def pause_task(
        self,
        task_id: str,
        *,
        project_id: str | None,
        reason: str,
        severity: str,
        rule_ids: tuple[str, ...],
        trace_id: str,
    ) -> str:
        """Block the task, record immutable evidence, and notify executives."""

        if (
            self._lifecycle_service.mark_blocked_dispatch(
                task_id,
                error_code="auditor_enforcement",
                message=reason,
                dispatch_target="auditor",
                outcome_source="auditor_enforcement",
            )
            is None
        ):
            raise AuditorFindingError(f"auditor pause failed: task not found: {task_id}")

        durable_project_id = _require_project_scope(
            project_id,
            trace_id=trace_id,
            operation="pause_task",
        )
        finding_pointer = self._governance_repo.write_project_artifact(
            project_id=durable_project_id,
            artifact_type="auditor_enforcement",
            content=_serialize_payload(
                {
                    "event_type": "auditor_enforcement",
                    "author_role": "auditor",
                    "task_id": task_id,
                    "project_id": durable_project_id,
                    "severity": _normalize_severity(severity),
                    "rule_ids": list(rule_ids),
                    "rationale": reason,
                    "trace_id": trace_id,
                    "incident_type": "task_pause",
                    "current_owner_role": "auditor",
                    "next_owner_role": "owner",
                    "path_reference": "auditor->owner",
                    "created_at": _utc_now_iso(),
                }
            ),
            write_context=_AUDITOR_WRITE_CONTEXT,
        )
        self._audit_writer.write_event(
            event_type="auditor_enforcement",
            outcome="blocked",
            trace_id=trace_id,
            request_id=None,
            task_id=task_id,
            principal_id="auditor",
            principal_role="auditor",
            source="auditor",
            reason_code="auditor_pause",
            message=reason,
            policy_version="v2",
            policy_hash="auditor-v1",
            rule_ids=rule_ids,
            payload={
                "project_id": durable_project_id,
                "severity": _normalize_severity(severity),
                "incident_type": "task_pause",
                "current_owner_role": "auditor",
                "next_owner_role": "owner",
                "path_reference": "auditor->owner",
            },
            attributes={
                "auditor.project_id": durable_project_id,
                "auditor.severity": _normalize_severity(severity),
            },
        )
        self._write_notification_artifact(
            project_id=durable_project_id,
            artifact_type="auditor_ceo_notification",
            trace_id=trace_id,
            content={
                "event_type": "auditor_ceo_notification",
                "author_role": "auditor",
                "task_id": task_id,
                "project_id": durable_project_id,
                "severity": _normalize_severity(severity),
                "rule_ids": list(rule_ids),
                "rationale": reason,
                "trace_id": trace_id,
                "incident_type": "task_pause",
                "current_owner_role": "auditor",
                "next_owner_role": "ceo",
                "path_reference": "auditor->ceo",
                "created_at": _utc_now_iso(),
            },
        )
        if _normalize_severity(severity) == "critical":
            self._write_notification_artifact(
                project_id=durable_project_id,
                artifact_type="auditor_owner_alert",
                trace_id=trace_id,
                content={
                    "event_type": "auditor_owner_alert",
                    "author_role": "auditor",
                    "task_id": task_id,
                    "project_id": durable_project_id,
                    "severity": "critical",
                    "rule_ids": list(rule_ids),
                    "rationale": reason,
                    "trace_id": trace_id,
                    "incident_type": "task_pause",
                    "current_owner_role": "auditor",
                    "next_owner_role": "owner",
                    "path_reference": "auditor->owner",
                    "created_at": _utc_now_iso(),
                },
            )
        return finding_pointer.storage_uri

    def escalate_to_owner(
        self,
        *,
        project_id: str | None,
        rule_ids: tuple[str, ...],
        rationale: str,
        severity: str,
        trace_id: str,
    ) -> str:
        """Create an immutable owner-bound escalation record."""

        durable_project_id = _require_project_scope(
            project_id,
            trace_id=trace_id,
            operation="escalate_to_owner",
        )
        pointer = self._governance_repo.write_project_artifact(
            project_id=durable_project_id,
            artifact_type="auditor_owner_escalation",
            content=_serialize_payload(
                {
                    "event_type": "auditor_owner_escalation",
                    "author_role": "auditor",
                    "project_id": durable_project_id,
                    "severity": _normalize_severity(severity),
                    "rule_ids": list(rule_ids),
                    "rationale": rationale,
                    "trace_id": trace_id,
                    "incident_type": "governance_escalation",
                    "current_owner_role": "auditor",
                    "next_owner_role": "owner",
                    "path_reference": "auditor->owner",
                    "created_at": _utc_now_iso(),
                }
            ),
            write_context=_AUDITOR_WRITE_CONTEXT,
        )
        return pointer.storage_uri

    def record_finding(
        self,
        *,
        project_id: str | None,
        finding_type: str,
        rule_ids: tuple[str, ...],
        rationale: str,
        trace_id: str,
        task_id: str | None = None,
        source_agent_role: str | None = None,
        severity: str | None = None,
    ) -> str:
        """Write one immutable compliance finding record."""

        durable_project_id = _require_project_scope(
            project_id,
            trace_id=trace_id,
            operation="record_finding",
        )
        pointer = self._governance_repo.write_project_artifact(
            project_id=durable_project_id,
            artifact_type="auditor_finding",
            content=_serialize_payload(
                {
                    "event_type": "auditor_finding",
                    "author_role": "auditor",
                    "project_id": durable_project_id,
                    "finding_type": finding_type,
                    "severity": _normalize_severity(severity or "medium"),
                    "task_id": task_id,
                    "source_agent_role": _normalize_optional_text(source_agent_role),
                    "rule_ids": list(rule_ids),
                    "rationale": rationale,
                    "trace_id": trace_id,
                    "created_at": _utc_now_iso(),
                }
            ),
            write_context=_AUDITOR_WRITE_CONTEXT,
        )
        return pointer.storage_uri

    def _write_notification_artifact(
        self,
        *,
        project_id: str,
        artifact_type: str,
        trace_id: str,
        content: dict[str, object],
    ) -> str:
        # REVIEW_NOTE: the handoff requires CEO/owner delivery notifications and passes the
        # communication repository into this service, but the current runtime surface exposes
        # only the durable communication ledger here, not a publish-capable notifier. Record the
        # immutable notification evidence now and leave live-delivery orchestration to Architect.
        _ = PublishRequest
        _ = self._communication_repo
        pointer = self._governance_repo.write_project_artifact(
            project_id=project_id,
            artifact_type=artifact_type,
            content=_serialize_payload(content),
            write_context=_AUDITOR_WRITE_CONTEXT,
        )
        return pointer.storage_uri


def _require_project_scope(
    project_id: str | None,
    *,
    trace_id: str,
    operation: str,
) -> str:
    # REVIEW_NOTE: the handoff allows ``project_id=None`` on Auditor requests, but the governed
    # artifact repository is project-scoped only. Fail closed until the Architect specifies a
    # durable global/system scope for auditor evidence outside a project.
    normalized_project_id = _normalize_optional_text(project_id)
    if normalized_project_id is None:
        raise AuditorFindingError(
            f"{operation} requires project_id for durable auditor evidence (trace_id={trace_id})"
        )
    return normalized_project_id


def _normalize_severity(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"low", "medium", "high", "critical"}:
        return normalized
    return "high"


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _serialize_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True)


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()
