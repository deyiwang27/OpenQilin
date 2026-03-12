"""Governance repository primitives for project lifecycle persistence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Mapping
from uuid import uuid4

from openqilin.control_plane.governance.project_lifecycle import (
    ProjectLifecycleError,
    ProjectStatus,
    assert_project_transition,
    parse_project_status,
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
    initialized_at: datetime


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
    initialization: ProjectInitializationSnapshot | None = None


class InMemoryGovernanceRepository:
    """In-memory governance repository with canonical lifecycle enforcement."""

    def __init__(self) -> None:
        self._projects_by_id: dict[str, ProjectRecord] = {}

    def create_project(
        self,
        *,
        name: str,
        objective: str,
        project_id: str | None = None,
        status: str = "proposed",
        metadata: Mapping[str, object] | None = None,
    ) -> ProjectRecord:
        """Create one project record; creation status must be `proposed`."""

        normalized_status = parse_project_status(status)
        if normalized_status != "proposed":
            raise GovernanceRepositoryError(
                code="governance_project_invalid_create_state",
                message="project creation state must be proposed",
            )
        candidate_project_id = project_id or str(uuid4())
        if candidate_project_id in self._projects_by_id:
            raise GovernanceRepositoryError(
                code="governance_project_exists",
                message=f"project already exists: {candidate_project_id}",
            )
        timestamp = datetime.now(tz=UTC)
        project = ProjectRecord(
            project_id=candidate_project_id,
            name=name.strip(),
            objective=objective.strip(),
            status=normalized_status,
            created_at=timestamp,
            updated_at=timestamp,
            metadata=(
                tuple(sorted((str(key), str(value)) for key, value in metadata.items()))
                if metadata is not None
                else ()
            ),
        )
        self._projects_by_id[candidate_project_id] = project
        return project

    def get_project(self, project_id: str) -> ProjectRecord | None:
        """Load one project by identifier."""

        return self._projects_by_id.get(project_id)

    def list_projects(self) -> tuple[ProjectRecord, ...]:
        """List all projects sorted by creation timestamp and id."""

        return tuple(
            sorted(
                self._projects_by_id.values(),
                key=lambda project: (project.created_at, project.project_id),
            )
        )

    def transition_project_status(
        self,
        *,
        project_id: str,
        next_status: str,
        reason_code: str,
        actor_role: str,
        trace_id: str,
        metadata: Mapping[str, object] | None = None,
    ) -> ProjectRecord:
        """Apply one lifecycle transition using canonical project-state guards."""

        project = self._projects_by_id.get(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        try:
            normalized_next = assert_project_transition(project.status, next_status)
        except ProjectLifecycleError as error:
            raise GovernanceRepositoryError(code=error.code, message=error.message) from error

        transition = ProjectStatusTransitionRecord(
            project_id=project.project_id,
            from_status=project.status,
            to_status=normalized_next,
            reason_code=reason_code.strip(),
            actor_role=actor_role.strip(),
            trace_id=trace_id.strip(),
            timestamp=datetime.now(tz=UTC),
            metadata=(
                tuple(sorted((str(key), str(value)) for key, value in metadata.items()))
                if metadata is not None
                else ()
            ),
        )
        updated = replace(
            project,
            status=normalized_next,
            updated_at=transition.timestamp,
            transitions=project.transitions + (transition,),
        )
        self._projects_by_id[project_id] = updated
        return updated

    def add_proposal_message(
        self,
        *,
        project_id: str,
        actor_id: str,
        actor_role: str,
        content: str,
        trace_id: str,
    ) -> ProposalMessageRecord:
        """Persist one proposal-stage discussion message."""

        project = self._projects_by_id.get(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        if project.status != "proposed":
            raise GovernanceRepositoryError(
                code="governance_project_not_proposed",
                message="proposal discussions are only allowed while project status is proposed",
            )
        message = ProposalMessageRecord(
            message_id=str(uuid4()),
            project_id=project_id,
            actor_id=actor_id.strip(),
            actor_role=actor_role.strip(),
            content=content.strip(),
            trace_id=trace_id.strip(),
            timestamp=datetime.now(tz=UTC),
        )
        updated = replace(
            project,
            updated_at=message.timestamp,
            proposal_messages=project.proposal_messages + (message,),
        )
        self._projects_by_id[project_id] = updated
        return message

    def record_proposal_approval(
        self,
        *,
        project_id: str,
        actor_id: str,
        actor_role: str,
        trace_id: str,
    ) -> tuple[ProjectRecord, bool]:
        """Persist one proposal approval and auto-promote when triad is complete."""

        normalized_role = actor_role.strip()
        project = self._projects_by_id.get(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        if project.status != "proposed":
            raise GovernanceRepositoryError(
                code="governance_project_not_proposed",
                message="proposal approvals are only allowed while project status is proposed",
            )
        existing = next(
            (
                approval
                for approval in project.proposal_approvals
                if approval.actor_role == normalized_role
            ),
            None,
        )
        if existing is not None and existing.actor_id == actor_id.strip():
            return project, False
        if existing is not None and existing.actor_id != actor_id.strip():
            raise GovernanceRepositoryError(
                code="governance_approval_role_conflict",
                message=f"proposal role already approved by another actor: {normalized_role}",
            )

        approval = ProposalApprovalRecord(
            approval_id=str(uuid4()),
            project_id=project_id,
            actor_id=actor_id.strip(),
            actor_role=normalized_role,
            trace_id=trace_id.strip(),
            timestamp=datetime.now(tz=UTC),
        )
        updated = replace(
            project,
            updated_at=approval.timestamp,
            proposal_approvals=project.proposal_approvals + (approval,),
        )
        self._projects_by_id[project_id] = updated
        if self._has_triad_approvals(updated):
            promoted = self.transition_project_status(
                project_id=project_id,
                next_status="approved",
                reason_code="proposal_triad_approved",
                actor_role=normalized_role,
                trace_id=trace_id,
            )
            return promoted, True
        return updated, True

    @staticmethod
    def _has_triad_approvals(project: ProjectRecord) -> bool:
        roles = {approval.actor_role for approval in project.proposal_approvals}
        return {"owner", "ceo", "cwo"}.issubset(roles)

    def initialize_project(
        self,
        *,
        project_id: str,
        objective: str,
        budget_currency_total: float,
        budget_quota_total: float,
        metric_plan: Mapping[str, object] | None,
        workforce_plan: Mapping[str, object] | None,
        actor_id: str,
        actor_role: str,
        trace_id: str,
    ) -> ProjectRecord:
        """Persist CWO initialization charter and promote approved project to active."""

        project = self._projects_by_id.get(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        if project.status != "approved":
            raise GovernanceRepositoryError(
                code="governance_project_not_approved",
                message="project initialization requires approved status",
            )
        if project.initialization is not None:
            raise GovernanceRepositoryError(
                code="governance_project_already_initialized",
                message="project has already been initialized",
            )
        if budget_currency_total < 0 or budget_quota_total < 0:
            raise GovernanceRepositoryError(
                code="governance_project_invalid_budget",
                message="project budget totals must be non-negative",
            )

        snapshot = ProjectInitializationSnapshot(
            objective=objective.strip(),
            budget_currency_total=float(budget_currency_total),
            budget_quota_total=float(budget_quota_total),
            metric_plan=(
                tuple(sorted((str(key), str(value)) for key, value in metric_plan.items()))
                if metric_plan is not None
                else ()
            ),
            workforce_plan=(
                tuple(sorted((str(key), str(value)) for key, value in workforce_plan.items()))
                if workforce_plan is not None
                else ()
            ),
            actor_id=actor_id.strip(),
            actor_role=actor_role.strip(),
            trace_id=trace_id.strip(),
            initialized_at=datetime.now(tz=UTC),
        )
        updated = replace(
            project,
            objective=snapshot.objective,
            updated_at=snapshot.initialized_at,
            initialization=snapshot,
        )
        self._projects_by_id[project_id] = updated
        return self.transition_project_status(
            project_id=project_id,
            next_status="active",
            reason_code="cwo_project_initialization",
            actor_role=actor_role,
            trace_id=trace_id,
            metadata={
                "budget_currency_total": snapshot.budget_currency_total,
                "budget_quota_total": snapshot.budget_quota_total,
            },
        )
