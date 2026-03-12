"""Governance repository primitives for project lifecycle persistence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from textwrap import dedent
from typing import Mapping
from uuid import uuid4

from openqilin.control_plane.governance.project_lifecycle import (
    ProjectLifecycleError,
    ProjectStatus,
    assert_project_transition,
    parse_project_status,
)
from openqilin.data_access.repositories.artifacts import (
    InMemoryProjectArtifactRepository,
    ProjectArtifactRepositoryError,
    ProjectArtifactWriteContext,
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
    initialization: ProjectInitializationSnapshot | None = None
    workforce_bindings: tuple[WorkforceBindingRecord, ...] = ()


class InMemoryGovernanceRepository:
    """In-memory governance repository with canonical lifecycle enforcement."""

    def __init__(
        self,
        *,
        artifact_repository: InMemoryProjectArtifactRepository | None = None,
    ) -> None:
        self._projects_by_id: dict[str, ProjectRecord] = {}
        self._artifact_repository = artifact_repository

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

        pointers = self._persist_initialization_artifacts(
            project_id=project_id,
            objective=objective.strip(),
            budget_currency_total=float(budget_currency_total),
            budget_quota_total=float(budget_quota_total),
            metric_plan=metric_plan,
            workforce_plan=workforce_plan,
            actor_role=actor_role.strip(),
            project_status=project.status,
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
            charter_storage_uri=pointers.get("project_charter_storage_uri"),
            charter_content_hash=pointers.get("project_charter_content_hash"),
            scope_statement_storage_uri=pointers.get("scope_statement_storage_uri"),
            scope_statement_content_hash=pointers.get("scope_statement_content_hash"),
            budget_plan_storage_uri=pointers.get("budget_plan_storage_uri"),
            budget_plan_content_hash=pointers.get("budget_plan_content_hash"),
            metric_plan_storage_uri=pointers.get("success_metrics_storage_uri"),
            metric_plan_content_hash=pointers.get("success_metrics_content_hash"),
            workforce_plan_storage_uri=pointers.get("workforce_plan_storage_uri"),
            workforce_plan_content_hash=pointers.get("workforce_plan_content_hash"),
            execution_plan_storage_uri=pointers.get("execution_plan_storage_uri"),
            execution_plan_content_hash=pointers.get("execution_plan_content_hash"),
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
                "charter_storage_uri": snapshot.charter_storage_uri or "",
                "scope_statement_storage_uri": snapshot.scope_statement_storage_uri or "",
                "budget_plan_storage_uri": snapshot.budget_plan_storage_uri or "",
                "metric_plan_storage_uri": snapshot.metric_plan_storage_uri or "",
                "workforce_plan_storage_uri": snapshot.workforce_plan_storage_uri or "",
                "execution_plan_storage_uri": snapshot.execution_plan_storage_uri or "",
            },
        )

    def _persist_initialization_artifacts(
        self,
        *,
        project_id: str,
        objective: str,
        budget_currency_total: float,
        budget_quota_total: float,
        metric_plan: Mapping[str, object] | None,
        workforce_plan: Mapping[str, object] | None,
        actor_role: str,
        project_status: str,
    ) -> dict[str, str]:
        if self._artifact_repository is None:
            return {}
        write_context = ProjectArtifactWriteContext(
            actor_role=actor_role,
            project_status=project_status,
            approval_roles=("ceo", "cwo"),
        )
        try:
            charter_pointer = self._artifact_repository.write_project_artifact(
                project_id=project_id,
                artifact_type="project_charter",
                content=self._render_project_charter(objective=objective),
                write_context=write_context,
            )
            scope_pointer = self._artifact_repository.write_project_artifact(
                project_id=project_id,
                artifact_type="scope_statement",
                content=self._render_scope_statement(objective=objective),
                write_context=write_context,
            )
            budget_pointer = self._artifact_repository.write_project_artifact(
                project_id=project_id,
                artifact_type="budget_plan",
                content=self._render_budget_plan(
                    budget_currency_total=budget_currency_total,
                    budget_quota_total=budget_quota_total,
                ),
                write_context=write_context,
            )
            metric_pointer = self._artifact_repository.write_project_artifact(
                project_id=project_id,
                artifact_type="success_metrics",
                content=self._render_mapping_document(
                    title="Success Metrics",
                    values=metric_plan,
                ),
                write_context=write_context,
            )
            workforce_pointer = self._artifact_repository.write_project_artifact(
                project_id=project_id,
                artifact_type="workforce_plan",
                content=self._render_mapping_document(
                    title="Workforce Plan",
                    values=workforce_plan,
                ),
                write_context=write_context,
            )
            execution_pointer = self._artifact_repository.write_project_artifact(
                project_id=project_id,
                artifact_type="execution_plan",
                content=self._render_execution_plan(workforce_plan=workforce_plan),
                write_context=write_context,
            )
            if not self._artifact_repository.verify_pointer_hash(
                project_id=project_id,
                artifact_type="project_charter",
            ):
                raise GovernanceRepositoryError(
                    code="governance_project_artifact_integrity_failed",
                    message="project charter pointer/hash verification failed",
                )
            if not self._artifact_repository.verify_pointer_hash(
                project_id=project_id,
                artifact_type="scope_statement",
            ):
                raise GovernanceRepositoryError(
                    code="governance_project_artifact_integrity_failed",
                    message="scope statement pointer/hash verification failed",
                )
            if not self._artifact_repository.verify_pointer_hash(
                project_id=project_id,
                artifact_type="budget_plan",
            ):
                raise GovernanceRepositoryError(
                    code="governance_project_artifact_integrity_failed",
                    message="budget plan pointer/hash verification failed",
                )
            if not self._artifact_repository.verify_pointer_hash(
                project_id=project_id,
                artifact_type="success_metrics",
            ):
                raise GovernanceRepositoryError(
                    code="governance_project_artifact_integrity_failed",
                    message="success metrics pointer/hash verification failed",
                )
            if not self._artifact_repository.verify_pointer_hash(
                project_id=project_id,
                artifact_type="workforce_plan",
            ):
                raise GovernanceRepositoryError(
                    code="governance_project_artifact_integrity_failed",
                    message="workforce plan pointer/hash verification failed",
                )
            if not self._artifact_repository.verify_pointer_hash(
                project_id=project_id,
                artifact_type="execution_plan",
            ):
                raise GovernanceRepositoryError(
                    code="governance_project_artifact_integrity_failed",
                    message="execution plan pointer/hash verification failed",
                )
        except ProjectArtifactRepositoryError as error:
            if error.code in {
                "artifact_type_not_allowed",
                "artifact_type_cap_exceeded",
                "artifact_project_total_cap_exceeded",
                "artifact_write_context_missing",
                "artifact_write_project_read_only",
                "artifact_write_role_forbidden",
                "artifact_write_project_manager_inactive",
                "artifact_write_project_manager_forbidden_type",
                "artifact_write_project_manager_approval_missing",
            }:
                raise GovernanceRepositoryError(
                    code="governance_project_artifact_policy_denied",
                    message=error.message,
                ) from error
            raise GovernanceRepositoryError(
                code="governance_project_artifact_persistence_failed",
                message=error.message,
            ) from error

        return {
            "project_charter_storage_uri": charter_pointer.storage_uri,
            "project_charter_content_hash": charter_pointer.content_hash,
            "scope_statement_storage_uri": scope_pointer.storage_uri,
            "scope_statement_content_hash": scope_pointer.content_hash,
            "budget_plan_storage_uri": budget_pointer.storage_uri,
            "budget_plan_content_hash": budget_pointer.content_hash,
            "success_metrics_storage_uri": metric_pointer.storage_uri,
            "success_metrics_content_hash": metric_pointer.content_hash,
            "workforce_plan_storage_uri": workforce_pointer.storage_uri,
            "workforce_plan_content_hash": workforce_pointer.content_hash,
            "execution_plan_storage_uri": execution_pointer.storage_uri,
            "execution_plan_content_hash": execution_pointer.content_hash,
        }

    @staticmethod
    def _render_project_charter(*, objective: str) -> str:
        return dedent(
            f"""\
            # Project Charter

            ## Objective
            {objective}
            """
        ).strip()

    @staticmethod
    def _render_scope_statement(*, objective: str) -> str:
        return dedent(
            f"""\
            # Scope Statement

            ## Scope Intent
            {objective}
            """
        ).strip()

    @staticmethod
    def _render_budget_plan(
        *,
        budget_currency_total: float,
        budget_quota_total: float,
    ) -> str:
        return dedent(
            f"""\
            # Budget Plan

            - currency_usd_total: {budget_currency_total:.2f}
            - quota_units_total: {budget_quota_total:.2f}
            """
        ).strip()

    @staticmethod
    def _render_execution_plan(*, workforce_plan: Mapping[str, object] | None) -> str:
        workforce_lines = (
            "\n".join(
                f"- {str(key)}: {str(value)}"
                for key, value in sorted(workforce_plan.items(), key=lambda item: str(item[0]))
            )
            if workforce_plan
            else "- (empty)"
        )
        return dedent(
            f"""\
            # Execution Plan

            ## Workforce Baseline
            {workforce_lines}

            ## Mandatory Project Manager Operations
            - milestone_planning
            - task_decomposition
            - task_assignment
            - progress_reporting
            """
        ).strip()

    @staticmethod
    def _render_mapping_document(*, title: str, values: Mapping[str, object] | None) -> str:
        if values is None or len(values) == 0:
            body = "- (empty)"
        else:
            body = "\n".join(
                f"- {str(key)}: {str(value)}"
                for key, value in sorted(values.items(), key=lambda item: str(item[0]))
            )
        return dedent(
            f"""\
            # {title}

            {body}
            """
        ).strip()

    def bind_workforce_template(
        self,
        *,
        project_id: str,
        role: str,
        template_id: str,
        llm_routing_profile: str,
        system_prompt_hash: str,
        mandatory_operations: tuple[str, ...] = (),
        actor_id: str,
        actor_role: str,
        trace_id: str,
    ) -> WorkforceBindingRecord:
        """Persist one workforce template binding for Project Manager or Domain Leader."""

        project = self._projects_by_id.get(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        if project.status != "active":
            raise GovernanceRepositoryError(
                code="governance_project_not_active",
                message="workforce template binding requires active project status",
            )

        normalized_role = role.strip().lower()
        if normalized_role not in {"project_manager", "domain_leader"}:
            raise GovernanceRepositoryError(
                code="governance_workforce_role_invalid",
                message=f"unsupported workforce role: {normalized_role}",
            )
        if normalized_role == "project_manager":
            existing_pm = next(
                (
                    binding
                    for binding in project.workforce_bindings
                    if binding.role == "project_manager" and binding.binding_status == "active"
                ),
                None,
            )
            if existing_pm is not None:
                raise GovernanceRepositoryError(
                    code="governance_project_manager_binding_exists",
                    message="project manager binding already exists for project",
                )
            if len(mandatory_operations) == 0:
                raise GovernanceRepositoryError(
                    code="governance_project_manager_template_missing_operations",
                    message=("project manager template must include mandatory operations contract"),
                )

        binding_status = "active" if normalized_role == "project_manager" else "declared_disabled"
        binding = WorkforceBindingRecord(
            binding_id=str(uuid4()),
            project_id=project_id,
            role=normalized_role,
            template_id=template_id.strip(),
            llm_routing_profile=llm_routing_profile.strip(),
            system_prompt_hash=system_prompt_hash.strip(),
            mandatory_operations=tuple(sorted(set(mandatory_operations))),
            binding_status=binding_status,
            actor_id=actor_id.strip(),
            actor_role=actor_role.strip(),
            trace_id=trace_id.strip(),
            created_at=datetime.now(tz=UTC),
        )
        updated = replace(
            project,
            updated_at=binding.created_at,
            workforce_bindings=project.workforce_bindings + (binding,),
        )
        self._projects_by_id[project_id] = updated
        return binding
