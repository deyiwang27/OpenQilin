"""Administrator agent implementation."""

from __future__ import annotations

import json
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Callable

from openqilin.agents.administrator.document_policy import DocumentPolicyEnforcer
from openqilin.agents.administrator.models import (
    AdministratorError,
    AdministratorRequest,
    AdministratorResponse,
)
from openqilin.agents.administrator.retention import RetentionEnforcer
from openqilin.agents.auditor.enforcement import AuditWriter
from openqilin.data_access.repositories.agent_registry import AgentRegistryRepositoryError
from openqilin.data_access.repositories.artifacts import ProjectArtifactWriteContext
from openqilin.data_access.repositories.postgres.agent_registry_repository import (
    PostgresAgentRegistryRepository,
)
from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
    PostgresGovernanceArtifactRepository,
)

if TYPE_CHECKING:
    pass

_SYSTEM_PROJECT_ID = "system"
_ALLOWED_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
_ADMINISTRATOR_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="administrator",
    project_status="active",
)


class AdministratorAgent:
    """Infrastructure and document-policy enforcement authority (oversight only)."""

    def __init__(
        self,
        document_policy: DocumentPolicyEnforcer,
        retention: RetentionEnforcer,
        governance_repo: PostgresGovernanceArtifactRepository,
        agent_registry_repo: PostgresAgentRegistryRepository,
        audit_writer: AuditWriter,
        trace_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._document_policy = document_policy
        self._retention = retention
        self._governance_repo = governance_repo
        self._agent_registry_repo = agent_registry_repo
        self._audit_writer = audit_writer
        self._trace_id_factory = trace_id_factory or (lambda: str(uuid.uuid4()))

    def handle(self, request: AdministratorRequest) -> AdministratorResponse:
        """Dispatch to the appropriate administrator action."""

        normalized_request = _normalize_request(request, trace_id_factory=self._trace_id_factory)
        if normalized_request.action == "check_artifact_cap":
            return self._handle_check_artifact_cap(normalized_request)
        if normalized_request.action == "enforce_retention":
            return self._handle_enforce_retention(normalized_request)
        if normalized_request.action == "quarantine_agent":
            return self._handle_quarantine_agent(normalized_request)
        if normalized_request.action == "query":
            return AdministratorResponse(
                action_taken="no_action",
                audit_record_id=None,
                oversight_text="Oversight query acknowledged. No enforcement action taken.",
                trace_id=normalized_request.trace_id,
            )
        return AdministratorResponse(
            action_taken="no_action",
            audit_record_id=None,
            oversight_text=(f"Unsupported administrator action: {normalized_request.action!r}."),
            trace_id=normalized_request.trace_id,
        )

    def _handle_check_artifact_cap(self, request: AdministratorRequest) -> AdministratorResponse:
        """Requires project_id and artifact_type. Returns cap_allowed or cap_denied."""

        project_id = _require_text(request.project_id, "check_artifact_cap requires project_id")
        artifact_type = _require_text(
            request.artifact_type,
            "check_artifact_cap requires artifact_type",
        )
        result = self._document_policy.check_artifact_cap(
            project_id=project_id,
            artifact_type=artifact_type,
            trace_id=request.trace_id,
        )
        if result.allowed:
            return AdministratorResponse(
                action_taken="cap_allowed",
                audit_record_id=None,
                oversight_text="Artifact cap check passed.",
                trace_id=request.trace_id,
            )
        return AdministratorResponse(
            action_taken="cap_denied",
            audit_record_id=None,
            oversight_text=result.denial_reason or "Cap denied.",
            trace_id=request.trace_id,
        )

    def _handle_enforce_retention(self, request: AdministratorRequest) -> AdministratorResponse:
        """Requires project_id. Routes to RetentionEnforcer based on reason content."""

        project_id = _require_text(request.project_id, "enforce_retention requires project_id")
        reason = request.reason.lower()
        if "terminat" in reason:
            audit_record_id = self._retention.enforce_terminated_project(
                project_id=project_id,
                trace_id=request.trace_id,
            )
        else:
            audit_record_id = self._retention.enforce_completed_project(
                project_id=project_id,
                trace_id=request.trace_id,
            )
        return AdministratorResponse(
            action_taken="retention_enforced",
            audit_record_id=audit_record_id,
            oversight_text="Retention enforced.",
            trace_id=request.trace_id,
        )

    def _handle_quarantine_agent(self, request: AdministratorRequest) -> AdministratorResponse:
        """Requires agent_id. Quarantines agent, notifies owner and CEO."""

        agent_id = _require_text(request.agent_id, "quarantine_agent requires agent_id")
        project_id = request.project_id or _SYSTEM_PROJECT_ID
        try:
            self._agent_registry_repo.quarantine_agent(
                agent_id=agent_id,
                reason=request.reason,
                trace_id=request.trace_id,
            )
        except AgentRegistryRepositoryError as exc:
            raise AdministratorError(str(exc)) from exc

        containment_pointer = self._write_governance_artifact(
            project_id=project_id,
            artifact_type="administrator_containment",
            payload={
                "event_type": "administrator_containment",
                "action": "agent_quarantined",
                "agent_id": agent_id,
                "reason": request.reason,
                "severity": request.severity,
                "rule_ids": ["AUTH-001", "GOV-001"],
                "trace_id": request.trace_id,
                "created_at": _utc_now_iso(),
            },
        )
        self._write_governance_artifact(
            project_id=project_id,
            artifact_type="administrator_owner_notification",
            payload={
                "event_type": "administrator_owner_notification",
                "action": "agent_quarantined",
                "agent_id": agent_id,
                "reason": request.reason,
                "severity": request.severity,
                "trace_id": request.trace_id,
                "next_owner_role": "owner",
                "created_at": _utc_now_iso(),
            },
        )
        self._write_governance_artifact(
            project_id=project_id,
            artifact_type="administrator_ceo_notification",
            payload={
                "event_type": "administrator_ceo_notification",
                "action": "agent_quarantined",
                "agent_id": agent_id,
                "reason": request.reason,
                "severity": request.severity,
                "trace_id": request.trace_id,
                "next_owner_role": "ceo",
                "created_at": _utc_now_iso(),
            },
        )
        if request.severity == "critical":
            self._write_governance_artifact(
                project_id=project_id,
                artifact_type="administrator_owner_alert",
                payload={
                    "event_type": "administrator_owner_alert",
                    "action": "agent_quarantined",
                    "agent_id": agent_id,
                    "reason": request.reason,
                    "severity": "critical",
                    "trace_id": request.trace_id,
                    "next_owner_role": "owner",
                    "created_at": _utc_now_iso(),
                },
            )
        self._audit_writer.write_event(
            event_type="administrator_containment",
            outcome="quarantined",
            trace_id=request.trace_id,
            request_id=None,
            task_id=None,
            principal_id="administrator",
            principal_role="administrator",
            source="administrator",
            reason_code="administrator_quarantine",
            message="agent quarantined",
            policy_version="v2",
            policy_hash="administrator-v1",
            rule_ids=["AUTH-001", "GOV-001"],
            payload={
                "project_id": project_id,
                "agent_id": agent_id,
                "severity": request.severity,
                "reason": request.reason,
            },
        )
        return AdministratorResponse(
            action_taken="agent_quarantined",
            audit_record_id=containment_pointer.storage_uri,
            oversight_text="Agent quarantined. Owner and CEO notified.",
            trace_id=request.trace_id,
        )

    def _write_governance_artifact(
        self,
        *,
        project_id: str,
        artifact_type: str,
        payload: dict[str, object],
    ):
        return self._governance_repo.write_project_artifact(
            project_id=project_id,
            artifact_type=artifact_type,
            content=json.dumps(payload, sort_keys=True),
            write_context=_ADMINISTRATOR_WRITE_CONTEXT,
        )


def _normalize_request(
    request: AdministratorRequest,
    *,
    trace_id_factory: Callable[[], str],
) -> AdministratorRequest:
    normalized_action = request.action.strip().lower()
    normalized_severity = request.severity.strip().lower()
    if normalized_severity not in _ALLOWED_SEVERITIES:
        normalized_severity = "high"
    normalized_trace_id = request.trace_id.strip() or trace_id_factory()
    return replace(
        request,
        action=normalized_action,
        project_id=_normalize_optional_text(request.project_id),
        agent_id=_normalize_optional_text(request.agent_id),
        artifact_type=_normalize_optional_text(request.artifact_type, lower=True),
        reason=request.reason.strip(),
        severity=normalized_severity,
        rule_ids=tuple(str(rule_id) for rule_id in request.rule_ids),
        trace_id=normalized_trace_id,
    )


def _normalize_optional_text(value: str | None, *, lower: bool = False) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if lower:
        return normalized.lower()
    return normalized


def _require_text(value: str | None, message: str) -> str:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise AdministratorError(message)
    return normalized


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()
