"""Governance repository primitives for project lifecycle persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from openqilin.control_plane.governance.project_lifecycle import (
    ProjectStatus,
)


class GovernanceRepositoryError(ValueError):
    """Raised when governance repository operations violate runtime contract."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class ProjectStatusTransitionRecord:
    """Append-only transition record for project status changes."""

    project_id: str
    from_status: ProjectStatus
    to_status: ProjectStatus
    reason_code: str
    actor_role: str
    trace_id: str
    timestamp: datetime
    metadata: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ProposalMessageRecord:
    """Persisted proposal discussion message in proposed stage."""

    message_id: str
    project_id: str
    actor_id: str
    actor_role: str
    content: str
    trace_id: str
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class ProposalApprovalRecord:
    """Persisted proposal approval decision by triad role."""

    approval_id: str
    project_id: str
    actor_id: str
    actor_role: str
    trace_id: str
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class CompletionReportRecord:
    """Persisted completion report submitted by Project Manager."""

    report_id: str
    project_id: str
    actor_id: str
    actor_role: str
    summary: str
    metric_results: tuple[tuple[str, str], ...]
    trace_id: str
    completion_report_storage_uri: str | None
    completion_report_content_hash: str | None
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class CompletionApprovalRecord:
    """Persisted completion approval decision by CWO/CEO."""

    approval_id: str
    project_id: str
    actor_id: str
    actor_role: str
    trace_id: str
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class ProjectInitializationSnapshot:
    """Persisted CWO initialization charter for one project."""

    objective: str
    budget_currency_total: float
    budget_quota_total: float
    metric_plan: tuple[tuple[str, str], ...]
    workforce_plan: tuple[tuple[str, str], ...]
    actor_id: str
    actor_role: str
    trace_id: str
    charter_storage_uri: str | None
    charter_content_hash: str | None
    scope_statement_storage_uri: str | None
    scope_statement_content_hash: str | None
    budget_plan_storage_uri: str | None
    budget_plan_content_hash: str | None
    metric_plan_storage_uri: str | None
    metric_plan_content_hash: str | None
    workforce_plan_storage_uri: str | None
    workforce_plan_content_hash: str | None
    execution_plan_storage_uri: str | None
    execution_plan_content_hash: str | None
    initialized_at: datetime


@dataclass(frozen=True, slots=True)
class WorkforceBindingRecord:
    """Persisted workforce template binding under project governance control."""

    binding_id: str
    project_id: str
    role: str
    template_id: str
    llm_routing_profile: str
    system_prompt_hash: str
    mandatory_operations: tuple[str, ...]
    binding_status: str
    actor_id: str
    actor_role: str
    trace_id: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectRecord:
    """Persisted governance project state."""

    project_id: str
    name: str
    objective: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    metadata: tuple[tuple[str, str], ...]
    transitions: tuple[ProjectStatusTransitionRecord, ...] = ()
    proposal_messages: tuple[ProposalMessageRecord, ...] = ()
    proposal_approvals: tuple[ProposalApprovalRecord, ...] = ()
    completion_report: CompletionReportRecord | None = None
    completion_approvals: tuple[CompletionApprovalRecord, ...] = ()
    completion_owner_notified_at: datetime | None = None
    completion_owner_notification_trace_id: str | None = None
    initialization: ProjectInitializationSnapshot | None = None
    workforce_bindings: tuple[WorkforceBindingRecord, ...] = ()
