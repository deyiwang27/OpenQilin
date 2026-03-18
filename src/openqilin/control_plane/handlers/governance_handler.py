"""Governance handler primitives for proposal discussion and approval flow."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping
from uuid import uuid4

from openqilin.control_plane.governance.project_manager_template import (
    ProjectManagerTemplateError,
    validate_project_manager_template,
)
from openqilin.data_access.repositories.governance import (
    CompletionReportRecord,
    GovernanceRepositoryError,
    ProjectInitializationSnapshot,
    ProjectRecord,
    ProposalApprovalRecord,
    ProposalMessageRecord,
    WorkforceBindingRecord,
)
from openqilin.data_access.repositories.postgres.project_repository import PostgresProjectRepository

UTC = timezone.utc

_TRIAD_ROLES = frozenset({"owner", "ceo", "cwo"})


class GovernanceHandlerError(ValueError):
    """Raised when governance handler validation or repository calls fail."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class ProposalApprovalOutcome:
    """Outcome returned by proposal approval command handling."""

    project: ProjectRecord
    approval_recorded: bool
    approval_roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectCreateOutcome:
    """Outcome returned by proposal-stage project creation."""

    project: ProjectRecord


@dataclass(frozen=True, slots=True)
class ProjectInitializationOutcome:
    """Outcome returned by CWO project initialization workflow."""

    project: ProjectRecord


@dataclass(frozen=True, slots=True)
class WorkforceBindingOutcome:
    """Outcome returned by CWO workforce template binding operation."""

    project: ProjectRecord
    role: str
    binding_status: str
    template_id: str
    llm_routing_profile: str
    system_prompt_hash: str
    mandatory_operations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectCompletionReportOutcome:
    """Outcome returned when Project Manager submits completion report."""

    project: ProjectRecord
    report: CompletionReportRecord


@dataclass(frozen=True, slots=True)
class ProjectCompletionApprovalOutcome:
    """Outcome returned when CEO/CWO records completion approval."""

    project: ProjectRecord
    approval_recorded: bool
    approval_roles: tuple[str, ...]
    owner_notified: bool


@dataclass(frozen=True, slots=True)
class ProjectCompletionFinalizeOutcome:
    """Outcome returned when completion transition is finalized."""

    project: ProjectRecord


@dataclass(frozen=True, slots=True)
class ProjectLifecycleTransitionOutcome:
    """Outcome returned by governed lifecycle transition actions."""

    project: ProjectRecord
    previous_status: str
    reason_code: str


def submit_proposal_message(
    *,
    repository: PostgresProjectRepository,
    project_id: str,
    actor_id: str,
    actor_role: str,
    content: str,
    trace_id: str,
) -> ProposalMessageRecord:
    """Validate and persist proposal-stage discussion message."""

    normalized_role = actor_role.strip().lower()
    if normalized_role not in _TRIAD_ROLES:
        raise GovernanceHandlerError(
            code="governance_role_forbidden",
            message="proposal discussions are limited to owner, ceo, and cwo",
        )
    try:
        return repository.add_proposal_message(
            project_id=project_id,
            actor_id=actor_id,
            actor_role=normalized_role,
            content=content,
            trace_id=trace_id,
        )
    except GovernanceRepositoryError as error:
        raise GovernanceHandlerError(code=error.code, message=error.message) from error


def create_project_proposal(
    *,
    repository: PostgresProjectRepository,
    actor_id: str,
    actor_role: str,
    trace_id: str,
    name: str,
    objective: str,
    project_id: str | None,
    metadata: Mapping[str, object] | None = None,
) -> ProjectCreateOutcome:
    """Create proposal-stage project under triad governance scope."""

    normalized_role = actor_role.strip().lower()
    if normalized_role not in _TRIAD_ROLES:
        raise GovernanceHandlerError(
            code="governance_project_create_role_forbidden",
            message="project creation is limited to owner, ceo, and cwo",
        )
    merged_metadata = dict(metadata or {})
    merged_metadata.setdefault("created_by_actor_id", actor_id.strip())
    merged_metadata.setdefault("created_by_actor_role", normalized_role)
    merged_metadata.setdefault("created_trace_id", trace_id.strip())
    try:
        project = repository.create_project(
            project_id=project_id,
            name=name,
            objective=objective,
            status="proposed",
            metadata=merged_metadata,
        )
    except GovernanceRepositoryError as error:
        raise GovernanceHandlerError(code=error.code, message=error.message) from error
    return ProjectCreateOutcome(project=project)


def approve_project_proposal(
    *,
    repository: PostgresProjectRepository,
    project_id: str,
    actor_id: str,
    actor_role: str,
    trace_id: str,
) -> ProposalApprovalOutcome:
    """Validate and persist triad approvals; auto-promote project when complete."""

    normalized_role = actor_role.strip().lower()
    if normalized_role not in _TRIAD_ROLES:
        raise GovernanceHandlerError(
            code="governance_approval_role_forbidden",
            message="proposal approval is limited to owner, ceo, and cwo",
        )
    try:
        project, approval_recorded = repository.record_proposal_approval(
            project_id=project_id,
            actor_id=actor_id,
            actor_role=normalized_role,
            trace_id=trace_id,
        )
    except GovernanceRepositoryError as error:
        raise GovernanceHandlerError(code=error.code, message=error.message) from error

    approval_roles = tuple(sorted({approval.actor_role for approval in project.proposal_approvals}))
    return ProposalApprovalOutcome(
        project=project,
        approval_recorded=approval_recorded,
        approval_roles=approval_roles,
    )


def latest_approval_for_role(
    project: ProjectRecord,
    *,
    role: str,
) -> ProposalApprovalRecord | None:
    """Fetch latest approval for one role from persisted proposal approvals."""

    for approval in reversed(project.proposal_approvals):
        if approval.actor_role == role:
            return approval
    return None


def initialize_project_by_cwo(
    *,
    repository: PostgresProjectRepository,
    project_id: str,
    actor_id: str,
    actor_role: str,
    trace_id: str,
    objective: str,
    budget_currency_total: float,
    budget_quota_total: float,
    metric_plan: Mapping[str, object] | None,
    workforce_plan: Mapping[str, object] | None,
) -> ProjectInitializationOutcome:
    """Run CWO-only project initialization contract and activate project."""

    normalized_role = actor_role.strip().lower()
    if normalized_role != "cwo":
        raise GovernanceHandlerError(
            code="governance_role_forbidden",
            message="project initialization is limited to cwo",
        )

    def _to_pair_tuple(m: Mapping[str, object] | None) -> tuple[tuple[str, str], ...]:
        if m is None:
            return ()
        return tuple((str(k), str(v)) for k, v in m.items())

    snapshot = ProjectInitializationSnapshot(
        objective=objective,
        budget_currency_total=budget_currency_total,
        budget_quota_total=budget_quota_total,
        metric_plan=_to_pair_tuple(metric_plan),
        workforce_plan=_to_pair_tuple(workforce_plan),
        actor_id=actor_id,
        actor_role=normalized_role,
        trace_id=trace_id,
        charter_storage_uri=None,
        charter_content_hash=None,
        scope_statement_storage_uri=None,
        scope_statement_content_hash=None,
        budget_plan_storage_uri=None,
        budget_plan_content_hash=None,
        metric_plan_storage_uri=None,
        metric_plan_content_hash=None,
        workforce_plan_storage_uri=None,
        workforce_plan_content_hash=None,
        execution_plan_storage_uri=None,
        execution_plan_content_hash=None,
        initialized_at=datetime.now(tz=UTC),
    )
    try:
        project = repository.record_initialization(
            project_id=project_id,
            snapshot=snapshot,
        )
    except GovernanceRepositoryError as error:
        raise GovernanceHandlerError(code=error.code, message=error.message) from error
    return ProjectInitializationOutcome(project=project)


def submit_completion_report_by_project_manager(
    *,
    repository: PostgresProjectRepository,
    project_id: str,
    actor_id: str,
    actor_role: str,
    trace_id: str,
    summary: str,
    metric_results: Mapping[str, object] | None,
) -> ProjectCompletionReportOutcome:
    """Persist completion report under Project Manager governance contract."""

    normalized_role = actor_role.strip().lower()
    if normalized_role != "project_manager":
        raise GovernanceHandlerError(
            code="governance_project_completion_report_role_forbidden",
            message="completion report submission is limited to project_manager",
        )
    try:
        report = repository.submit_completion_report(
            project_id=project_id,
            actor_id=actor_id,
            actor_role=normalized_role,
            summary=summary,
            metric_results=metric_results,
            trace_id=trace_id,
        )
    except GovernanceRepositoryError as error:
        raise GovernanceHandlerError(code=error.code, message=error.message) from error
    project = repository.get_project(project_id)
    if project is None:
        raise GovernanceHandlerError(
            code="governance_project_missing",
            message=f"project not found: {project_id}",
        )
    return ProjectCompletionReportOutcome(project=project, report=report)


def record_completion_approval_by_c_suite(
    *,
    repository: PostgresProjectRepository,
    project_id: str,
    actor_id: str,
    actor_role: str,
    trace_id: str,
) -> ProjectCompletionApprovalOutcome:
    """Persist completion approval decision under CEO/CWO contract."""

    normalized_role = actor_role.strip().lower()
    if normalized_role not in {"ceo", "cwo"}:
        raise GovernanceHandlerError(
            code="governance_project_completion_approval_role_forbidden",
            message="completion approval is limited to ceo or cwo",
        )
    try:
        project, approval_recorded = repository.record_completion_approval(
            project_id=project_id,
            actor_id=actor_id,
            actor_role=normalized_role,
            trace_id=trace_id,
        )
    except GovernanceRepositoryError as error:
        raise GovernanceHandlerError(code=error.code, message=error.message) from error
    approval_roles = tuple(
        sorted({approval.actor_role for approval in project.completion_approvals})
    )
    return ProjectCompletionApprovalOutcome(
        project=project,
        approval_recorded=approval_recorded,
        approval_roles=approval_roles,
        owner_notified=project.completion_owner_notified_at is not None,
    )


def finalize_project_completion_by_c_suite(
    *,
    repository: PostgresProjectRepository,
    project_id: str,
    actor_role: str,
    trace_id: str,
    reason_code: str,
) -> ProjectCompletionFinalizeOutcome:
    """Finalize project completion after completion governance prerequisites are met."""

    normalized_role = actor_role.strip().lower()
    if normalized_role not in {"ceo", "cwo"}:
        raise GovernanceHandlerError(
            code="governance_project_completion_finalize_role_forbidden",
            message="completion finalization is limited to ceo or cwo",
        )
    try:
        project = repository.transition_project_status(
            project_id=project_id,
            next_status="completed",
            reason_code=reason_code,
            actor_role=normalized_role,
            trace_id=trace_id,
        )
    except GovernanceRepositoryError as error:
        raise GovernanceHandlerError(code=error.code, message=error.message) from error
    return ProjectCompletionFinalizeOutcome(project=project)


def _transition_project_lifecycle(
    *,
    repository: PostgresProjectRepository,
    project_id: str,
    actor_role: str,
    trace_id: str,
    reason_code: str,
    next_status: str,
    allowed_actor_roles: frozenset[str],
    action_name: str,
) -> ProjectLifecycleTransitionOutcome:
    """Apply one lifecycle transition with explicit actor-role guardrails."""

    normalized_role = actor_role.strip().lower()
    if normalized_role not in allowed_actor_roles:
        allowed_roles = ",".join(sorted(allowed_actor_roles))
        raise GovernanceHandlerError(
            code="governance_project_lifecycle_role_forbidden",
            message=f"{action_name} is limited to roles: {allowed_roles}",
        )
    project = repository.get_project(project_id)
    if project is None:
        raise GovernanceHandlerError(
            code="governance_project_missing",
            message=f"project not found: {project_id}",
        )
    previous_status = project.status
    try:
        updated = repository.transition_project_status(
            project_id=project_id,
            next_status=next_status,
            reason_code=reason_code,
            actor_role=normalized_role,
            trace_id=trace_id,
        )
    except GovernanceRepositoryError as error:
        raise GovernanceHandlerError(code=error.code, message=error.message) from error
    return ProjectLifecycleTransitionOutcome(
        project=updated,
        previous_status=previous_status,
        reason_code=reason_code,
    )


def pause_project_by_governance(
    *,
    repository: PostgresProjectRepository,
    project_id: str,
    actor_role: str,
    trace_id: str,
    reason_code: str,
) -> ProjectLifecycleTransitionOutcome:
    """Pause one active project under governed role matrix."""

    return _transition_project_lifecycle(
        repository=repository,
        project_id=project_id,
        actor_role=actor_role,
        trace_id=trace_id,
        reason_code=reason_code,
        next_status="paused",
        allowed_actor_roles=frozenset({"project_manager", "cwo", "ceo"}),
        action_name="project pause",
    )


def resume_project_by_governance(
    *,
    repository: PostgresProjectRepository,
    project_id: str,
    actor_role: str,
    trace_id: str,
    reason_code: str,
) -> ProjectLifecycleTransitionOutcome:
    """Resume one paused project under governed role matrix."""

    return _transition_project_lifecycle(
        repository=repository,
        project_id=project_id,
        actor_role=actor_role,
        trace_id=trace_id,
        reason_code=reason_code,
        next_status="active",
        allowed_actor_roles=frozenset({"project_manager", "cwo", "ceo"}),
        action_name="project resume",
    )


def terminate_project_by_governance(
    *,
    repository: PostgresProjectRepository,
    project_id: str,
    actor_role: str,
    trace_id: str,
    reason_code: str,
) -> ProjectLifecycleTransitionOutcome:
    """Terminate one project from active or paused state under governed role matrix."""

    return _transition_project_lifecycle(
        repository=repository,
        project_id=project_id,
        actor_role=actor_role,
        trace_id=trace_id,
        reason_code=reason_code,
        next_status="terminated",
        allowed_actor_roles=frozenset({"cwo", "ceo"}),
        action_name="project termination",
    )


def archive_project_by_governance(
    *,
    repository: PostgresProjectRepository,
    project_id: str,
    actor_role: str,
    trace_id: str,
    reason_code: str,
) -> ProjectLifecycleTransitionOutcome:
    """Archive one completed or terminated project under governed role matrix."""

    return _transition_project_lifecycle(
        repository=repository,
        project_id=project_id,
        actor_role=actor_role,
        trace_id=trace_id,
        reason_code=reason_code,
        next_status="archived",
        allowed_actor_roles=frozenset({"cwo", "ceo"}),
        action_name="project archive",
    )


def bind_workforce_template_by_cwo(
    *,
    repository: PostgresProjectRepository,
    project_id: str,
    actor_id: str,
    actor_role: str,
    trace_id: str,
    role: str,
    template_id: str,
    llm_routing_profile: str,
    system_prompt: str,
) -> WorkforceBindingOutcome:
    """Bind workforce template package under CWO-only governance contract."""

    normalized_actor_role = actor_role.strip().lower()
    if normalized_actor_role != "cwo":
        raise GovernanceHandlerError(
            code="governance_role_forbidden",
            message="workforce template binding is limited to cwo",
        )
    normalized_role = role.strip().lower()
    mandatory_operations: tuple[str, ...] = ()
    if normalized_role == "project_manager":
        try:
            validation = validate_project_manager_template(system_prompt)
        except ProjectManagerTemplateError as error:
            raise GovernanceHandlerError(
                code=f"governance_{error.code}",
                message=error.message,
            ) from error
        mandatory_operations = tuple(sorted(validation.mandatory_operations))

    system_prompt_hash = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()
    # DL agent is declared_disabled until OPA policy runtime is live (M12 gate)
    binding_status = "declared_disabled" if normalized_role == "domain_leader" else "active"
    binding_record = WorkforceBindingRecord(
        binding_id=str(uuid4()),
        project_id=project_id,
        role=normalized_role,
        template_id=template_id,
        llm_routing_profile=llm_routing_profile,
        system_prompt_hash=system_prompt_hash,
        mandatory_operations=mandatory_operations,
        binding_status=binding_status,
        actor_id=actor_id,
        actor_role=normalized_actor_role,
        trace_id=trace_id,
        created_at=datetime.now(tz=UTC),
    )
    try:
        project = repository.bind_workforce(
            project_id=project_id,
            binding=binding_record,
        )
    except GovernanceRepositoryError as error:
        raise GovernanceHandlerError(code=error.code, message=error.message) from error

    return WorkforceBindingOutcome(
        project=project,
        role=binding_record.role,
        binding_status=binding_record.binding_status,
        template_id=binding_record.template_id,
        llm_routing_profile=binding_record.llm_routing_profile,
        system_prompt_hash=binding_record.system_prompt_hash,
        mandatory_operations=binding_record.mandatory_operations,
    )
