"""Governance handler primitives for proposal discussion and approval flow."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from openqilin.control_plane.governance.project_manager_template import (
    ProjectManagerTemplateError,
    validate_project_manager_template,
)
from openqilin.data_access.repositories.governance import (
    GovernanceRepositoryError,
    InMemoryGovernanceRepository,
    ProjectRecord,
    ProposalApprovalRecord,
    ProposalMessageRecord,
)

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


def submit_proposal_message(
    *,
    repository: InMemoryGovernanceRepository,
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


def approve_project_proposal(
    *,
    repository: InMemoryGovernanceRepository,
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
    repository: InMemoryGovernanceRepository,
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
    try:
        project = repository.initialize_project(
            project_id=project_id,
            objective=objective,
            budget_currency_total=budget_currency_total,
            budget_quota_total=budget_quota_total,
            metric_plan=metric_plan,
            workforce_plan=workforce_plan,
            actor_id=actor_id,
            actor_role=normalized_role,
            trace_id=trace_id,
        )
    except GovernanceRepositoryError as error:
        raise GovernanceHandlerError(code=error.code, message=error.message) from error
    return ProjectInitializationOutcome(project=project)


def bind_workforce_template_by_cwo(
    *,
    repository: InMemoryGovernanceRepository,
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
        mandatory_operations = validation.mandatory_operations

    system_prompt_hash = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()
    try:
        binding = repository.bind_workforce_template(
            project_id=project_id,
            role=normalized_role,
            template_id=template_id,
            llm_routing_profile=llm_routing_profile,
            system_prompt_hash=system_prompt_hash,
            mandatory_operations=mandatory_operations,
            actor_id=actor_id,
            actor_role=normalized_actor_role,
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
    return WorkforceBindingOutcome(
        project=project,
        role=binding.role,
        binding_status=binding.binding_status,
        template_id=binding.template_id,
        llm_routing_profile=binding.llm_routing_profile,
        system_prompt_hash=binding.system_prompt_hash,
        mandatory_operations=binding.mandatory_operations,
    )
