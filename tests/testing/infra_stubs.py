"""Test-only in-memory infrastructure stubs.

These classes replace the deleted InMemory* infrastructure stubs that were
removed from src/ in M13-WP9.  They implement the same interface as the
real Postgres/Redis repositories so existing unit tests continue to work.

IMPORTANT: These stubs live in tests/ and MUST NOT be imported by production
code.  The CI grep gate (grep -r "class InMemory" src/) enforces this.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping, cast
from uuid import uuid4

from openqilin.control_plane.governance.project_lifecycle import ProjectStatus
from openqilin.data_access.repositories.artifacts import (
    _GOVERNANCE_EVENT_ARTIFACT_TYPES,
    ProjectArtifactDocument,
    ProjectArtifactPointer,
    ProjectArtifactRepositoryError,
    ProjectArtifactWriteContext,
    ProjectDocumentPolicy,
)
from openqilin.data_access.repositories.communication import (
    CommunicationDeadLetterRecord,
    CommunicationMessageRecord,
    CommunicationStateTransition,
)
from openqilin.data_access.repositories.governance import (
    CompletionApprovalRecord,
    CompletionReportRecord,
    GovernanceRepositoryError,
    ProjectInitializationSnapshot,
    ProjectRecord,
    ProjectStatusTransitionRecord,
    ProposalApprovalRecord,
    ProposalMessageRecord,
    WorkforceBindingRecord,
)
from openqilin.data_access.repositories.postgres.communication_repository import (
    PostgresCommunicationRepository,
)
from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
    PostgresGovernanceArtifactRepository,
)
from openqilin.data_access.repositories.postgres.identity_repository import (
    PostgresIdentityMappingRepository,
)
from openqilin.data_access.repositories.postgres.project_repository import (
    PostgresProjectRepository,
)
from openqilin.data_access.repositories.postgres.task_repository import (
    PostgresTaskRepository,
)
from openqilin.data_access.cache.idempotency_store import (
    CacheIdempotencyRecord,
    CacheIdempotencyStatus,
)
from openqilin.data_access.repositories.identity_channels import (
    IdentityChannelMappingRecord,
    IdentityChannelStatus,
)
from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.task_orchestrator.admission.envelope_validator import AdmissionEnvelope
from openqilin.task_orchestrator.state.transition_guard import assert_legal_transition


# ---------------------------------------------------------------------------
# InMemoryRuntimeStateRepository
# ---------------------------------------------------------------------------


class InMemoryRuntimeStateRepository(PostgresTaskRepository):
    """Test-only in-memory runtime state repository.

    No filesystem snapshot: PostgreSQL is the durable store (H-3 fix).
    """

    def __init__(self) -> None:  # type: ignore[override]
        self._task_by_id: dict[str, TaskRecord] = {}
        self._task_id_by_principal_key: dict[tuple[str, str], str] = {}

    def create_task_from_envelope(self, envelope: AdmissionEnvelope) -> TaskRecord:
        task = TaskRecord(
            task_id=str(uuid4()),
            request_id=envelope.request_id,
            trace_id=envelope.trace_id,
            principal_id=envelope.principal_id,
            principal_role=envelope.principal_role,
            trust_domain=envelope.trust_domain,
            connector=envelope.connector,
            command=envelope.command,
            target=envelope.target,
            args=envelope.args,
            metadata=envelope.metadata,
            project_id=envelope.project_id,
            idempotency_key=envelope.idempotency_key,
            status="queued",
            created_at=datetime.now(tz=UTC),
        )
        self._task_by_id[task.task_id] = task
        self._task_id_by_principal_key[(task.principal_id, task.idempotency_key)] = task.task_id
        return task

    def get_task_by_id(self, task_id: str) -> TaskRecord | None:
        return self._task_by_id.get(task_id)

    def get_task_by_principal_and_idempotency(
        self,
        principal_id: str,
        idempotency_key: str,
    ) -> TaskRecord | None:
        task_id = self._task_id_by_principal_key.get((principal_id, idempotency_key))
        if task_id is None:
            return None
        return self._task_by_id.get(task_id)

    def update_task_status(
        self,
        task_id: str,
        status: str,
        *,
        outcome_source: str | None = None,
        outcome_error_code: str | None = None,
        outcome_message: str | None = None,
        outcome_details: Mapping[str, object] | None = None,
        dispatch_target: str | None = None,
        dispatch_id: str | None = None,
    ) -> TaskRecord | None:
        task = self._task_by_id.get(task_id)
        if task is None:
            return None
        if task.status != status:
            assert_legal_transition(task.status, status)
        updated = replace(
            task,
            status=status,
            outcome_source=outcome_source if outcome_source is not None else task.outcome_source,
            outcome_error_code=(
                outcome_error_code if outcome_error_code is not None else task.outcome_error_code
            ),
            outcome_message=(
                outcome_message if outcome_message is not None else task.outcome_message
            ),
            outcome_details=(
                tuple(sorted((str(k), str(v)) for k, v in outcome_details.items()))
                if outcome_details is not None
                else task.outcome_details
            ),
            dispatch_target=(
                dispatch_target if dispatch_target is not None else task.dispatch_target
            ),
            dispatch_id=dispatch_id if dispatch_id is not None else task.dispatch_id,
        )
        self._task_by_id[task_id] = updated
        return updated

    def list_tasks(self) -> tuple[TaskRecord, ...]:
        return tuple(self._task_by_id.values())


def _task_to_dict(task: TaskRecord) -> dict[str, object]:
    return {
        "task_id": task.task_id,
        "request_id": task.request_id,
        "trace_id": task.trace_id,
        "principal_id": task.principal_id,
        "principal_role": task.principal_role,
        "trust_domain": task.trust_domain,
        "connector": task.connector,
        "command": task.command,
        "target": task.target,
        "args": list(task.args),
        "metadata": [list(m) for m in task.metadata],
        "project_id": task.project_id,
        "idempotency_key": task.idempotency_key,
        "status": task.status,
        "outcome_source": task.outcome_source,
        "outcome_error_code": task.outcome_error_code,
        "outcome_message": task.outcome_message,
        "outcome_details": [list(d) for d in (task.outcome_details or ())],
        "dispatch_target": task.dispatch_target,
        "dispatch_id": task.dispatch_id,
        "created_at": task.created_at.isoformat(),
    }


def _task_from_dict(d: dict[str, object]) -> TaskRecord:
    raw_args = d.get("args") or []
    raw_metadata = d.get("metadata") or []
    raw_outcome = d.get("outcome_details") or []
    return TaskRecord(
        task_id=str(d["task_id"]),
        request_id=str(d["request_id"]),
        trace_id=str(d["trace_id"]),
        principal_id=str(d["principal_id"]),
        principal_role=str(d["principal_role"]),
        trust_domain=str(d["trust_domain"]),
        connector=str(d["connector"]),
        command=str(d["command"]),
        target=str(d["target"]),
        args=tuple(str(a) for a in cast(list[object], raw_args)),
        metadata=tuple(
            (str(pair[0]), str(pair[1]))  # type: ignore[index]
            for pair in cast(list[object], raw_metadata)
        ),
        project_id=str(d["project_id"]) if d.get("project_id") else None,
        idempotency_key=str(d["idempotency_key"]),
        status=str(d["status"]),
        outcome_source=str(d["outcome_source"]) if d.get("outcome_source") else None,
        outcome_error_code=(str(d["outcome_error_code"]) if d.get("outcome_error_code") else None),
        outcome_message=str(d["outcome_message"]) if d.get("outcome_message") else None,
        outcome_details=tuple(
            (str(pair[0]), str(pair[1]))  # type: ignore[index]
            for pair in cast(list[object], raw_outcome)
        ),
        dispatch_target=str(d["dispatch_target"]) if d.get("dispatch_target") else None,
        dispatch_id=str(d["dispatch_id"]) if d.get("dispatch_id") else None,
        created_at=datetime.fromisoformat(str(d["created_at"])),
    )


# ---------------------------------------------------------------------------
# InMemoryGovernanceRepository (implements PostgresProjectRepository interface)
# ---------------------------------------------------------------------------


_TRIAD_ROLES = frozenset({"owner", "ceo", "cwo"})
_COMPLETION_APPROVAL_ROLES = frozenset({"cwo", "ceo"})


def _cast_status(s: str) -> ProjectStatus:
    return cast(ProjectStatus, s)


class InMemoryGovernanceRepository(PostgresProjectRepository):
    """Test-only in-memory governance repository (PostgresProjectRepository API)."""

    def __init__(  # type: ignore[override]
        self,
        *,
        artifact_repository: InMemoryProjectArtifactRepository | None = None,
    ) -> None:
        self._projects: dict[str, ProjectRecord] = {}
        self._artifact_repository = artifact_repository
        # Note: does NOT call super().__init__() — no real DB session needed in tests

    def get_project(self, project_id: str) -> ProjectRecord | None:
        return self._projects.get(project_id)

    def list_projects(self) -> tuple[ProjectRecord, ...]:
        return tuple(self._projects.values())

    def create_project(
        self,
        *,
        project_id: str | None = None,
        name: str,
        objective: str,
        status: str = "proposed",
        metadata: Mapping[str, object] | None = None,
    ) -> ProjectRecord:
        pid = project_id or str(uuid4())
        if status != "proposed":
            raise GovernanceRepositoryError(
                code="governance_project_invalid_create_state",
                message=f"projects must be created in proposed state, got: {status}",
            )
        if pid in self._projects:
            raise GovernanceRepositoryError(
                code="governance_project_duplicate",
                message=f"project already exists: {pid}",
            )
        now = datetime.now(tz=UTC)
        meta: tuple[tuple[str, str], ...] = tuple(
            (str(k), str(v)) for k, v in (metadata or {}).items()
        )
        project = ProjectRecord(
            project_id=pid,
            name=name,
            objective=objective,
            status=_cast_status(status),
            metadata=meta,
            transitions=(),
            proposal_messages=(),
            proposal_approvals=(),
            completion_report=None,
            completion_approvals=(),
            completion_owner_notified_at=None,
            initialization=None,
            workforce_bindings=(),
            created_at=now,
            updated_at=now,
        )
        self._projects[pid] = project
        return project

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
        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        # Enforce lifecycle transition rules
        try:
            from openqilin.control_plane.governance.project_lifecycle import (
                assert_project_transition,
            )

            assert_project_transition(project.status, next_status)
        except Exception as exc:
            raise GovernanceRepositoryError(
                code="project_invalid_transition",
                message=str(exc),
            ) from exc
        # Enforce completion report prerequisite
        if next_status == "completed" and project.completion_report is None:
            raise GovernanceRepositoryError(
                code="governance_project_completion_report_missing",
                message="completion report required before completing project",
            )
        now = datetime.now(tz=UTC)
        transition = ProjectStatusTransitionRecord(
            project_id=project_id,
            from_status=project.status,
            to_status=_cast_status(next_status),
            reason_code=reason_code,
            actor_role=actor_role,
            trace_id=trace_id,
            timestamp=now,
            metadata=(),
        )
        updated = replace(
            project,
            status=_cast_status(next_status),
            transitions=project.transitions + (transition,),
            updated_at=now,
        )
        self._projects[project_id] = updated
        return updated

    def initialize_project(
        self,
        *,
        project_id: str,
        objective: str,
        budget_currency_total: float,
        budget_quota_total: float,
        metric_plan: Mapping[str, object],
        workforce_plan: Mapping[str, object],
        actor_id: str,
        actor_role: str,
        trace_id: str,
    ) -> ProjectRecord:
        """Legacy API shim — creates initialization snapshot and optionally writes artifacts."""
        now = datetime.now(tz=UTC)

        # Write artifacts to artifact_repository if available
        write_ctx = ProjectArtifactWriteContext(
            actor_role=actor_role,
            project_status="approved",
            approval_roles=("ceo", "cwo"),
        )
        charter_uri: str | None = None
        charter_hash: str | None = None
        scope_uri: str | None = None
        scope_hash: str | None = None
        budget_uri: str | None = None
        budget_hash: str | None = None
        metric_uri: str | None = None
        metric_hash: str | None = None
        workforce_uri: str | None = None
        workforce_hash: str | None = None
        exec_uri: str | None = None
        exec_hash: str | None = None

        if self._artifact_repository is not None:
            _artifacts_to_write = [
                ("project_charter", f"# Charter\n\n{objective}"),
                ("scope_statement", f"# Scope Statement\n\n{objective}"),
                (
                    "budget_plan",
                    f"# Budget Plan\n\nCurrency: {budget_currency_total}\nQuota: {budget_quota_total}",
                ),
                (
                    "success_metrics",
                    "# Success Metrics\n\n"
                    + "\n".join(f"- {k}: {v}" for k, v in metric_plan.items()),
                ),
                (
                    "workforce_plan",
                    "# Workforce Plan\n\n"
                    + "\n".join(f"- {k}: {v}" for k, v in workforce_plan.items()),
                ),
                ("execution_plan", "# Execution Plan\n\nPlan TBD"),
            ]
            pointers = {}
            for art_type, art_content in _artifacts_to_write:
                try:
                    ptr = self._artifact_repository.write_project_artifact(
                        project_id=project_id,
                        artifact_type=art_type,
                        content=art_content,
                        write_context=write_ctx,
                    )
                except ProjectArtifactRepositoryError as exc:
                    raise GovernanceRepositoryError(
                        code="governance_project_artifact_policy_denied",
                        message=f"artifact policy denied for {art_type}: {exc.message}",
                    ) from exc
                pointers[art_type] = ptr
            charter_uri = pointers["project_charter"].storage_uri
            charter_hash = pointers["project_charter"].content_hash
            scope_uri = pointers["scope_statement"].storage_uri
            scope_hash = pointers["scope_statement"].content_hash
            budget_uri = pointers["budget_plan"].storage_uri
            budget_hash = pointers["budget_plan"].content_hash
            metric_uri = pointers["success_metrics"].storage_uri
            metric_hash = pointers["success_metrics"].content_hash
            workforce_uri = pointers["workforce_plan"].storage_uri
            workforce_hash = pointers["workforce_plan"].content_hash
            exec_uri = pointers["execution_plan"].storage_uri
            exec_hash = pointers["execution_plan"].content_hash

        snapshot = ProjectInitializationSnapshot(
            objective=objective,
            budget_currency_total=budget_currency_total,
            budget_quota_total=budget_quota_total,
            metric_plan=tuple((str(k), str(v)) for k, v in metric_plan.items()),
            workforce_plan=tuple((str(k), str(v)) for k, v in workforce_plan.items()),
            actor_id=actor_id,
            actor_role=actor_role,
            trace_id=trace_id,
            charter_storage_uri=charter_uri,
            charter_content_hash=charter_hash,
            scope_statement_storage_uri=scope_uri,
            scope_statement_content_hash=scope_hash,
            budget_plan_storage_uri=budget_uri,
            budget_plan_content_hash=budget_hash,
            metric_plan_storage_uri=metric_uri,
            metric_plan_content_hash=metric_hash,
            workforce_plan_storage_uri=workforce_uri,
            workforce_plan_content_hash=workforce_hash,
            execution_plan_storage_uri=exec_uri,
            execution_plan_content_hash=exec_hash,
            initialized_at=now,
        )
        return self.record_initialization(project_id=project_id, snapshot=snapshot)

    def add_proposal_message(
        self,
        *,
        project_id: str,
        actor_id: str,
        actor_role: str,
        content: str,
        trace_id: str,
    ) -> ProposalMessageRecord:
        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        if project.status != "proposed":
            raise GovernanceRepositoryError(
                code="governance_proposal_not_in_proposed_state",
                message=f"project is not in proposed state: {project.status}",
            )
        now = datetime.now(tz=UTC)
        msg = ProposalMessageRecord(
            message_id=str(uuid4()),
            project_id=project_id,
            actor_id=actor_id,
            actor_role=actor_role,
            content=content,
            trace_id=trace_id,
            timestamp=now,
        )
        updated = replace(
            project,
            proposal_messages=project.proposal_messages + (msg,),
            updated_at=now,
        )
        self._projects[project_id] = updated
        return msg

    def record_proposal_approval(
        self,
        *,
        project_id: str,
        actor_id: str,
        actor_role: str,
        trace_id: str,
    ) -> tuple[ProjectRecord, bool]:
        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        if project.status != "proposed":
            raise GovernanceRepositoryError(
                code="governance_proposal_not_in_proposed_state",
                message=f"project is not in proposed state: {project.status}",
            )
        existing_roles = {a.actor_role for a in project.proposal_approvals}
        approval_recorded = actor_role not in existing_roles
        now = datetime.now(tz=UTC)
        approval = ProposalApprovalRecord(
            approval_id=str(uuid4()),
            project_id=project_id,
            actor_id=actor_id,
            actor_role=actor_role,
            trace_id=trace_id,
            timestamp=now,
        )
        new_approvals = project.proposal_approvals + (approval,)
        all_roles = {a.actor_role for a in new_approvals}
        new_status: ProjectStatus = (
            "approved" if _TRIAD_ROLES.issubset(all_roles) else project.status
        )
        transitions = project.transitions
        if new_status != project.status:
            transition = ProjectStatusTransitionRecord(
                project_id=project_id,
                from_status=project.status,
                to_status=new_status,
                reason_code="triad_approval_complete",
                actor_role=actor_role,
                trace_id=trace_id,
                timestamp=now,
                metadata=(),
            )
            transitions = project.transitions + (transition,)
        updated = replace(
            project,
            proposal_approvals=new_approvals,
            status=new_status,
            transitions=transitions,
            updated_at=now,
        )
        self._projects[project_id] = updated
        return updated, approval_recorded

    def submit_completion_report(
        self,
        *,
        project_id: str,
        actor_id: str,
        actor_role: str,
        summary: str,
        metric_results: Mapping[str, object] | None,
        trace_id: str,
    ) -> CompletionReportRecord:
        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        if actor_role != "project_manager":
            raise GovernanceRepositoryError(
                code="governance_project_completion_report_role_forbidden",
                message=f"role {actor_role!r} is not allowed to submit completion report",
            )
        now = datetime.now(tz=UTC)
        metric_tuple: tuple[tuple[str, str], ...] = tuple(
            (str(k), str(v)) for k, v in (metric_results or {}).items()
        )
        report_id = str(uuid4())
        import hashlib

        report_hash = hashlib.sha256(summary.encode()).hexdigest()[:32]
        report = CompletionReportRecord(
            report_id=report_id,
            project_id=project_id,
            actor_id=actor_id,
            actor_role=actor_role,
            summary=summary,
            metric_results=metric_tuple,
            completion_report_storage_uri=f"projects/{project_id}/completion/report-{report_id}.md",
            completion_report_content_hash=report_hash,
            trace_id=trace_id,
            timestamp=now,
        )
        updated = replace(project, completion_report=report, updated_at=now)
        self._projects[project_id] = updated
        return report

    def record_completion_approval(
        self,
        *,
        project_id: str,
        actor_id: str,
        actor_role: str,
        trace_id: str,
    ) -> tuple[ProjectRecord, bool]:
        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        existing_roles = {a.actor_role for a in project.completion_approvals}
        approval_recorded = actor_role not in existing_roles
        now = datetime.now(tz=UTC)
        approval = CompletionApprovalRecord(
            approval_id=str(uuid4()),
            project_id=project_id,
            actor_id=actor_id,
            actor_role=actor_role,
            trace_id=trace_id,
            timestamp=now,
        )
        new_approvals = project.completion_approvals + (approval,)
        # Notify owner when both CWO and CEO have approved
        all_approval_roles = {a.actor_role for a in new_approvals}
        notified_at = project.completion_owner_notified_at
        notified_trace = project.completion_owner_notification_trace_id
        if _COMPLETION_APPROVAL_ROLES.issubset(all_approval_roles) and notified_at is None:
            notified_at = now
            notified_trace = trace_id
        updated = replace(
            project,
            completion_approvals=new_approvals,
            completion_owner_notified_at=notified_at,
            completion_owner_notification_trace_id=notified_trace,
            updated_at=now,
        )
        self._projects[project_id] = updated
        return updated, approval_recorded

    def record_completion_owner_notified(self, *, project_id: str, trace_id: str) -> ProjectRecord:
        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        now = datetime.now(tz=UTC)
        updated = replace(
            project,
            completion_owner_notified_at=now,
            completion_owner_notification_trace_id=trace_id,
            updated_at=now,
        )
        self._projects[project_id] = updated
        return updated

    def record_initialization(
        self,
        *,
        project_id: str,
        snapshot: ProjectInitializationSnapshot,
    ) -> ProjectRecord:
        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        if project.status != "approved":
            raise GovernanceRepositoryError(
                code="governance_project_not_approved",
                message=f"project must be in approved state to initialize, got: {project.status}",
            )
        # Write artifacts to artifact_repository if available (mirrors old InMemory behavior
        # that enforced artifact policy during record_initialization).
        if self._artifact_repository is not None:
            write_ctx = ProjectArtifactWriteContext(
                actor_role=snapshot.actor_role,
                project_status="approved",
                approval_roles=("ceo", "cwo"),
            )
            _artifacts_to_write = [
                ("project_charter", f"# Charter\n\n{snapshot.objective}"),
                ("scope_statement", f"# Scope Statement\n\n{snapshot.objective}"),
                (
                    "budget_plan",
                    f"# Budget Plan\n\nCurrency: {snapshot.budget_currency_total}\nQuota: {snapshot.budget_quota_total}",
                ),
                (
                    "success_metrics",
                    "# Success Metrics\n\n"
                    + "\n".join(f"- {k}: {v}" for k, v in snapshot.metric_plan),
                ),
                (
                    "workforce_plan",
                    "# Workforce Plan\n\n"
                    + "\n".join(f"- {k}: {v}" for k, v in snapshot.workforce_plan),
                ),
                ("execution_plan", "# Execution Plan\n\nPlan TBD"),
            ]
            for art_type, art_content in _artifacts_to_write:
                try:
                    self._artifact_repository.write_project_artifact(
                        project_id=project_id,
                        artifact_type=art_type,
                        content=art_content,
                        write_context=write_ctx,
                    )
                except ProjectArtifactRepositoryError as exc:
                    raise GovernanceRepositoryError(
                        code="governance_project_artifact_policy_denied",
                        message=f"artifact policy denied for {art_type}: {exc.message}",
                    ) from exc
        now = datetime.now(tz=UTC)
        # After initialization, project transitions to active
        now_ts = datetime.now(tz=UTC)
        transition = ProjectStatusTransitionRecord(
            project_id=project_id,
            from_status=project.status,
            to_status=_cast_status("active"),
            reason_code="project_initialized",
            actor_role=snapshot.actor_role,
            trace_id=snapshot.trace_id,
            timestamp=now_ts,
            metadata=(),
        )
        updated = replace(
            project,
            objective=snapshot.objective,
            initialization=snapshot,
            status=_cast_status("active"),
            transitions=project.transitions + (transition,),
            updated_at=now,
        )
        self._projects[project_id] = updated
        return updated

    def bind_workforce(
        self,
        *,
        project_id: str,
        binding: WorkforceBindingRecord,
    ) -> ProjectRecord:
        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        now = datetime.now(tz=UTC)
        updated = replace(
            project,
            workforce_bindings=project.workforce_bindings + (binding,),
            updated_at=now,
        )
        self._projects[project_id] = updated
        return updated


# ---------------------------------------------------------------------------
# InMemoryProjectArtifactRepository
# ---------------------------------------------------------------------------


class InMemoryProjectArtifactRepository(PostgresGovernanceArtifactRepository):
    """Test-only file-system-backed artifact repository.

    Writes actual files to disk under system_root/projects/{project_id}/docs/{type}/
    with names matching {type}--v{revision:03d}.md to match test expectations.
    """

    def __init__(  # type: ignore[override]
        self,
        *,
        system_root: Path | None = None,
        policy: ProjectDocumentPolicy | None = None,
    ) -> None:
        self._system_root = system_root or Path("/tmp/openqilin_test_artifacts")
        self._artifacts: list[ProjectArtifactPointer] = []
        self._content_store: dict[str, str] = {}  # storage_uri -> content
        self._policy = policy or ProjectDocumentPolicy.mvp_defaults()

    def _artifact_path(self, project_id: str, artifact_type: str, revision_no: int) -> Path:
        return (
            self._system_root
            / "projects"
            / project_id
            / "docs"
            / artifact_type
            / f"{artifact_type}--v{revision_no:03d}.md"
        )

    def write_project_artifact(
        self,
        *,
        project_id: str,
        artifact_type: str,
        content: str,
        write_context: ProjectArtifactWriteContext | None = None,
    ) -> ProjectArtifactPointer:
        import hashlib
        import re

        _PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
        _ARTIFACT_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

        if not _PROJECT_ID_RE.match(project_id):
            raise ProjectArtifactRepositoryError(
                code="artifact_project_id_invalid",
                message=f"invalid project_id: {project_id!r}",
            )
        if not _ARTIFACT_TYPE_RE.match(artifact_type):
            raise ProjectArtifactRepositoryError(
                code="artifact_type_invalid",
                message=f"invalid artifact_type: {artifact_type!r}",
            )
        if write_context is None:
            raise ProjectArtifactRepositoryError(
                code="artifact_write_context_missing",
                message="artifact write context is required for governed writes",
            )
        _validate_artifact_write_context(artifact_type, write_context)

        # Enforce policy caps
        cap = self._policy.cap_for_type(artifact_type)
        existing_of_type = [
            a
            for a in self._artifacts
            if a.project_id == project_id and a.artifact_type == artifact_type
        ]
        # Singletons (cap==1) can be updated (new revision), but append-only types cannot exceed cap
        is_singleton = cap == 1
        if not is_singleton and len(existing_of_type) >= cap:
            raise ProjectArtifactRepositoryError(
                code="artifact_type_cap_exceeded",
                message=f"cap exceeded for artifact type: {artifact_type}",
            )
        # For singleton types (cap==1), updating doesn't count toward total active doc cap
        # For append-only types, each revision counts toward total cap
        # Total active doc count = total revisions (excluding singleton over-writes)
        all_for_project = [a for a in self._artifacts if a.project_id == project_id]
        # Active total: singletons count once, append-only count each revision
        active_total = 0
        types_seen: set[str] = set()
        for a in all_for_project:
            type_cap = self._policy.allowed_type_caps.get(a.artifact_type, 0)
            if type_cap == 1:
                if a.artifact_type not in types_seen:
                    active_total += 1
                    types_seen.add(a.artifact_type)
            else:
                active_total += 1
        # Determine if this write would add to total
        is_singleton = cap == 1
        adds_to_total = not (is_singleton and len(existing_of_type) > 0)
        if (
            adds_to_total
            and artifact_type not in _GOVERNANCE_EVENT_ARTIFACT_TYPES
            and active_total >= self._policy.total_active_document_cap
        ):
            raise ProjectArtifactRepositoryError(
                code="artifact_project_total_cap_exceeded",
                message="total active document cap exceeded for project",
            )

        revision_no = len(existing_of_type) + 1
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        artifact_path = self._artifact_path(project_id, artifact_type, revision_no)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(content, encoding="utf-8")
        storage_uri = str(artifact_path)
        now = datetime.now(tz=UTC)
        pointer = ProjectArtifactPointer(
            project_id=project_id,
            artifact_type=artifact_type,
            revision_no=revision_no,
            storage_uri=storage_uri,
            content_hash=content_hash,
            byte_size=len(content.encode("utf-8")),
            created_at=now,
        )
        self._artifacts.append(pointer)
        self._content_store[storage_uri] = content
        return pointer

    def read_latest_artifact(
        self,
        project_id: str,
        artifact_type: str,
    ) -> ProjectArtifactDocument | None:
        """Return the most recent artifact revision for one project/type pair."""
        matching = [
            a
            for a in self._artifacts
            if a.project_id == project_id and a.artifact_type == artifact_type
        ]
        if not matching:
            return None
        latest = max(matching, key=lambda a: a.revision_no)
        try:
            content = Path(latest.storage_uri).read_text(encoding="utf-8")
        except OSError:
            content = self._content_store.get(latest.storage_uri, "")
        return ProjectArtifactDocument(pointer=latest, content=content)

    def verify_pointer_hash(
        self,
        project_id: str,
        artifact_type: str,
    ) -> bool:
        """Verify that the stored file hash matches the pointer content_hash."""
        import hashlib

        matching = [
            a
            for a in self._artifacts
            if a.project_id == project_id and a.artifact_type == artifact_type
        ]
        if not matching:
            return False
        latest = max(matching, key=lambda a: a.revision_no)
        try:
            content = Path(latest.storage_uri).read_text(encoding="utf-8")
        except OSError:
            return False
        actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return actual_hash == latest.content_hash

    def list_project_artifacts(
        self,
        project_id: str,
        *,
        artifact_type: str | None = None,
    ) -> tuple[ProjectArtifactPointer, ...]:
        return tuple(
            a
            for a in self._artifacts
            if a.project_id == project_id
            and (artifact_type is None or a.artifact_type == artifact_type)
        )

    def list_artifact_documents(
        self,
        *,
        project_id: str,
        artifact_type: str,
    ) -> tuple[ProjectArtifactDocument, ...]:
        documents: list[ProjectArtifactDocument] = []
        for pointer in self.list_project_artifacts(project_id, artifact_type=artifact_type):
            try:
                content = Path(pointer.storage_uri).read_text(encoding="utf-8")
            except OSError:
                content = self._content_store.get(pointer.storage_uri, "")
            documents.append(ProjectArtifactDocument(pointer=pointer, content=content))
        return tuple(documents)

    def list_artifact_documents_by_type(
        self,
        *,
        artifact_type: str,
    ) -> tuple[ProjectArtifactDocument, ...]:
        matching = [a for a in self._artifacts if a.artifact_type == artifact_type]
        documents: list[ProjectArtifactDocument] = []
        for pointer in sorted(
            matching,
            key=lambda item: (item.created_at, item.project_id, item.revision_no),
        ):
            try:
                content = Path(pointer.storage_uri).read_text(encoding="utf-8")
            except OSError:
                content = self._content_store.get(pointer.storage_uri, "")
            documents.append(ProjectArtifactDocument(pointer=pointer, content=content))
        return tuple(documents)


def _validate_artifact_write_context(artifact_type: str, ctx: ProjectArtifactWriteContext) -> None:
    from openqilin.data_access.repositories.artifacts import (
        _PROJECT_MANAGER_CONTROLLED_WRITE_TYPES,
        _PROJECT_MANAGER_FORBIDDEN_WRITE_TYPES,
        _PROJECT_WRITABLE_STATES,
    )

    project_status = ctx.project_status.strip().lower()
    if project_status not in _PROJECT_WRITABLE_STATES:
        raise ProjectArtifactRepositoryError(
            code="artifact_project_not_writable",
            message=f"project status does not allow artifact writes: {project_status}",
        )

    if ctx.actor_role == "project_manager":
        # project_manager requires active state (stricter than _PROJECT_WRITABLE_STATES)
        if ctx.project_status not in {"active"}:
            raise ProjectArtifactRepositoryError(
                code="artifact_write_project_manager_inactive",
                message=f"project_manager cannot write artifacts in status: {ctx.project_status}",
            )
        if artifact_type in _PROJECT_MANAGER_CONTROLLED_WRITE_TYPES:
            approval_set = set(ctx.approval_roles)
            if not ({"ceo", "cwo"}.issubset(approval_set)):
                raise ProjectArtifactRepositoryError(
                    code="artifact_write_project_manager_approval_missing",
                    message=f"ceo+cwo approval required for {artifact_type}",
                )
        if artifact_type in _PROJECT_MANAGER_FORBIDDEN_WRITE_TYPES:
            raise ProjectArtifactRepositoryError(
                code="artifact_write_role_forbidden",
                message=f"project_manager cannot write {artifact_type}",
            )


# ---------------------------------------------------------------------------
# InMemoryCommunicationRepository
# ---------------------------------------------------------------------------


class InMemoryCommunicationRepository(PostgresCommunicationRepository):
    """Test-only in-memory communication repository."""

    def __init__(self, *, snapshot_path: Path | None = None) -> None:  # type: ignore[override]
        self._records: dict[str, CommunicationMessageRecord] = {}
        self._dead_letters: dict[str, CommunicationDeadLetterRecord] = {}
        self._snapshot_path = snapshot_path
        if snapshot_path is not None and snapshot_path.exists():
            self._load_snapshot()

    def create_record(
        self,
        *,
        task_id: str,
        trace_id: str,
        message_id: str,
        external_message_id: str,
        connector: str,
        command: str,
        target: str,
        route_key: str,
        endpoint: str,
        attempt: int = 1,
    ) -> CommunicationMessageRecord:
        now = datetime.now(tz=UTC)
        record = CommunicationMessageRecord(
            ledger_id=str(uuid4()),
            task_id=task_id,
            trace_id=trace_id,
            message_id=message_id,
            external_message_id=external_message_id,
            connector=connector,
            command=command,
            target=target,
            route_key=route_key,
            endpoint=endpoint,
            attempt=attempt,
            state="prepared",
            dispatch_id=None,
            delivery_id=None,
            retryable=None,
            error_code=None,
            error_message=None,
            transitions=(),
            created_at=now,
            updated_at=now,
        )
        self._records[record.ledger_id] = record
        self._flush_snapshot()
        return record

    def append_transition(
        self,
        ledger_id: str,
        state: str,
        *,
        reason_code: str | None = None,
        message: str | None = None,
        retryable: bool | None = None,
        dispatch_id: str | None = None,
        delivery_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> CommunicationMessageRecord | None:
        from openqilin.data_access.repositories.communication import LedgerState

        record = self._records.get(ledger_id)
        if record is None:
            return None
        now = datetime.now(tz=UTC)
        t = CommunicationStateTransition(
            state=cast(LedgerState, state),
            changed_at=now,
            reason_code=reason_code or "",
            message=message or "",
            retryable=retryable,
        )
        updated = replace(
            record,
            state=cast(LedgerState, state),
            transitions=record.transitions + (t,),
            dispatch_id=dispatch_id if dispatch_id is not None else record.dispatch_id,
            delivery_id=delivery_id if delivery_id is not None else record.delivery_id,
            retryable=retryable if retryable is not None else record.retryable,
            error_code=error_code if error_code is not None else record.error_code,
            error_message=error_message if error_message is not None else record.error_message,
            updated_at=now,
        )
        self._records[ledger_id] = updated
        self._flush_snapshot()
        return updated

    def get_record(self, ledger_id: str) -> CommunicationMessageRecord | None:
        return self._records.get(ledger_id)

    def get_message_by_id(self, message_id: str) -> CommunicationMessageRecord | None:
        for r in self._records.values():
            if r.message_id == message_id:
                return r
        return None

    def list_messages_for_task(self, task_id: str) -> tuple[CommunicationMessageRecord, ...]:
        return tuple(r for r in self._records.values() if r.task_id == task_id)

    def create_dead_letter_record(
        self,
        *,
        task_id: str,
        trace_id: str,
        principal_id: str,
        idempotency_key: str,
        message_id: str,
        external_message_id: str,
        connector: str,
        command: str,
        target: str,
        route_key: str,
        endpoint: str,
        error_code: str,
        error_message: str,
        attempts: int,
        ledger_id: str | None = None,
    ) -> CommunicationDeadLetterRecord:
        now = datetime.now(tz=UTC)
        record = CommunicationDeadLetterRecord(
            dead_letter_id=str(uuid4()),
            task_id=task_id,
            trace_id=trace_id,
            principal_id=principal_id,
            idempotency_key=idempotency_key,
            message_id=message_id,
            external_message_id=external_message_id,
            connector=connector,
            command=command,
            target=target,
            route_key=route_key,
            endpoint=endpoint,
            error_code=error_code,
            error_message=error_message,
            attempts=attempts,
            ledger_id=ledger_id,
            created_at=now,
        )
        self._dead_letters[record.dead_letter_id] = record
        self._flush_snapshot()
        return record

    def get_dead_letter(self, dead_letter_id: str) -> CommunicationDeadLetterRecord | None:
        return self._dead_letters.get(dead_letter_id)

    def list_dead_letters(self) -> tuple[CommunicationDeadLetterRecord, ...]:
        return tuple(self._dead_letters.values())

    def list_dead_letter_records(self) -> tuple[CommunicationDeadLetterRecord, ...]:
        return tuple(self._dead_letters.values())

    def _load_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        try:
            payload = json.loads(self._snapshot_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        for raw in payload.get("records", []):
            rec = _comm_from_dict(raw)
            self._records[rec.ledger_id] = rec
        for raw in payload.get("dead_letters", []):
            dl = _dead_letter_from_dict(raw)
            self._dead_letters[dl.dead_letter_id] = dl

    def _flush_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "records": [_comm_to_dict(m) for m in self._records.values()],
            "dead_letters": [_dead_letter_to_dict(d) for d in self._dead_letters.values()],
        }
        self._snapshot_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8"
        )


def _comm_to_dict(m: CommunicationMessageRecord) -> dict[str, object]:
    return {
        "ledger_id": m.ledger_id,
        "task_id": m.task_id,
        "trace_id": m.trace_id,
        "message_id": m.message_id,
        "external_message_id": m.external_message_id,
        "connector": m.connector,
        "command": m.command,
        "target": m.target,
        "route_key": m.route_key,
        "endpoint": m.endpoint,
        "attempt": m.attempt,
        "state": m.state,
        "dispatch_id": m.dispatch_id,
        "delivery_id": m.delivery_id,
        "retryable": m.retryable,
        "error_code": m.error_code,
        "error_message": m.error_message,
        "transitions": [
            {
                "state": t.state,
                "changed_at": t.changed_at.isoformat(),
                "reason_code": t.reason_code,
                "message": t.message,
                "retryable": t.retryable,
            }
            for t in m.transitions
        ],
        "created_at": m.created_at.isoformat(),
        "updated_at": m.updated_at.isoformat(),
    }


def _comm_from_dict(d: dict[str, object]) -> CommunicationMessageRecord:
    from openqilin.data_access.repositories.communication import LedgerState

    raw_transitions = d.get("transitions") or []
    transitions = tuple(
        CommunicationStateTransition(
            state=cast(LedgerState, str(t["state"])),  # type: ignore[index]
            changed_at=datetime.fromisoformat(str(t["changed_at"])),  # type: ignore[index]
            reason_code=str(t["reason_code"]) if t.get("reason_code") else "",  # type: ignore[index]
            message=str(t["message"]) if t.get("message") else "",  # type: ignore[index]
            retryable=bool(t["retryable"]) if t.get("retryable") is not None else None,  # type: ignore[index]
        )
        for t in cast(list[dict[str, object]], raw_transitions)
    )
    return CommunicationMessageRecord(
        ledger_id=str(d["ledger_id"]),
        task_id=str(d["task_id"]),
        trace_id=str(d["trace_id"]),
        message_id=str(d["message_id"]),
        external_message_id=str(d["external_message_id"]),
        connector=str(d["connector"]),
        command=str(d["command"]),
        target=str(d["target"]),
        route_key=str(d["route_key"]),
        endpoint=str(d["endpoint"]),
        attempt=int(str(d.get("attempt", 1))),
        state=cast(LedgerState, str(d["state"])),
        dispatch_id=str(d["dispatch_id"]) if d.get("dispatch_id") else None,
        delivery_id=str(d["delivery_id"]) if d.get("delivery_id") else None,
        retryable=bool(d["retryable"]) if d.get("retryable") is not None else None,
        error_code=str(d["error_code"]) if d.get("error_code") else None,
        error_message=str(d["error_message"]) if d.get("error_message") else None,
        transitions=transitions,
        created_at=datetime.fromisoformat(str(d["created_at"])),
        updated_at=datetime.fromisoformat(str(d["updated_at"])),
    )


def _dead_letter_to_dict(dl: CommunicationDeadLetterRecord) -> dict[str, object]:
    return {
        "dead_letter_id": dl.dead_letter_id,
        "task_id": dl.task_id,
        "trace_id": dl.trace_id,
        "principal_id": dl.principal_id,
        "idempotency_key": dl.idempotency_key,
        "message_id": dl.message_id,
        "external_message_id": dl.external_message_id,
        "connector": dl.connector,
        "command": dl.command,
        "target": dl.target,
        "route_key": dl.route_key,
        "endpoint": dl.endpoint,
        "error_code": dl.error_code,
        "error_message": dl.error_message,
        "attempts": dl.attempts,
        "ledger_id": dl.ledger_id,
        "created_at": dl.created_at.isoformat(),
    }


def _dead_letter_from_dict(d: dict[str, object]) -> CommunicationDeadLetterRecord:
    return CommunicationDeadLetterRecord(
        dead_letter_id=str(d["dead_letter_id"]),
        task_id=str(d["task_id"]),
        trace_id=str(d["trace_id"]),
        principal_id=str(d["principal_id"]),
        idempotency_key=str(d["idempotency_key"]),
        message_id=str(d["message_id"]),
        external_message_id=str(d["external_message_id"]),
        connector=str(d["connector"]),
        command=str(d["command"]),
        target=str(d["target"]),
        route_key=str(d["route_key"]),
        endpoint=str(d["endpoint"]),
        error_code=str(d["error_code"]),
        error_message=str(d["error_message"]),
        attempts=int(str(d["attempts"])),
        ledger_id=str(d["ledger_id"]) if d.get("ledger_id") else None,
        created_at=datetime.fromisoformat(str(d["created_at"])),
    )


# ---------------------------------------------------------------------------
# InMemoryIdentityChannelRepository
# ---------------------------------------------------------------------------


class InMemoryIdentityChannelRepository(PostgresIdentityMappingRepository):
    """Test-only in-memory identity/channel mapping repository."""

    def __init__(self, *, snapshot_path: Path | None = None) -> None:  # type: ignore[override]
        self._mappings: dict[str, IdentityChannelMappingRecord] = {}
        self._snapshot_path = snapshot_path
        if snapshot_path is not None and snapshot_path.exists():
            self._load_snapshot()

    def claim_mapping(
        self,
        *,
        connector: str,
        actor_external_id: str,
        guild_id: str,
        channel_id: str,
        channel_type: str,
        principal_role: str = "owner",
    ) -> IdentityChannelMappingRecord:
        key = f"{connector}:{actor_external_id}:{guild_id}:{channel_id}"
        existing = self._mappings.get(key)
        if existing is not None:
            return existing
        now = datetime.now(tz=UTC)
        record = IdentityChannelMappingRecord(
            mapping_id=str(uuid4()),
            connector=connector,
            actor_external_id=actor_external_id,
            guild_id=guild_id,
            channel_id=channel_id,
            channel_type=channel_type,
            status="pending",
            created_at=now,
            updated_at=now,
            principal_role=principal_role,
        )
        self._mappings[key] = record
        self._flush_snapshot()
        return record

    def set_mapping_status(
        self,
        *,
        connector: str,
        actor_external_id: str,
        guild_id: str,
        channel_id: str,
        channel_type: str,
        status: str,
    ) -> IdentityChannelMappingRecord:
        key = f"{connector}:{actor_external_id}:{guild_id}:{channel_id}"
        existing = self._mappings.get(key)
        if existing is None:
            raise KeyError(f"mapping not found: {key}")
        now = datetime.now(tz=UTC)
        updated = replace(existing, status=cast(IdentityChannelStatus, status), updated_at=now)
        self._mappings[key] = updated
        self._flush_snapshot()
        return updated

    def get_mapping(
        self,
        *,
        connector: str,
        actor_external_id: str,
        guild_id: str,
        channel_id: str,
        channel_type: str | None = None,
    ) -> IdentityChannelMappingRecord | None:
        key = f"{connector}:{actor_external_id}:{guild_id}:{channel_id}"
        return self._mappings.get(key)

    def revoke_mapping(
        self,
        *,
        connector: str,
        actor_external_id: str,
        guild_id: str,
        channel_id: str,
    ) -> IdentityChannelMappingRecord | None:
        key = f"{connector}:{actor_external_id}:{guild_id}:{channel_id}"
        existing = self._mappings.get(key)
        if existing is None:
            return None
        now = datetime.now(tz=UTC)
        updated = replace(existing, status=cast(IdentityChannelStatus, "revoked"), updated_at=now)
        self._mappings[key] = updated
        self._flush_snapshot()
        return updated

    def get_by_connector_actor(
        self,
        connector: str,
        actor_external_id: str,
    ) -> IdentityChannelMappingRecord | None:
        """Return the first verified mapping for (connector, actor_external_id), or None."""
        normalized_connector = connector.strip().lower()
        normalized_actor = actor_external_id.strip()
        for record in self._mappings.values():
            if (
                record.connector.lower() == normalized_connector
                and record.actor_external_id == normalized_actor
                and record.status == "verified"
            ):
                return record
        return None

    def list_mappings(self) -> tuple[IdentityChannelMappingRecord, ...]:
        return tuple(self._mappings.values())

    def _load_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        try:
            payload = json.loads(self._snapshot_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        for raw in payload.get("mappings", []):
            rec = _mapping_from_dict(raw)
            key = f"{rec.connector}:{rec.actor_external_id}:{rec.guild_id}:{rec.channel_id}"
            self._mappings[key] = rec

    def _flush_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"mappings": [_mapping_to_dict(m) for m in self._mappings.values()]}
        self._snapshot_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8"
        )


def _mapping_to_dict(m: IdentityChannelMappingRecord) -> dict[str, object]:
    return {
        "mapping_id": m.mapping_id,
        "connector": m.connector,
        "actor_external_id": m.actor_external_id,
        "guild_id": m.guild_id,
        "channel_id": m.channel_id,
        "channel_type": m.channel_type,
        "status": m.status,
        "created_at": m.created_at.isoformat(),
        "updated_at": m.updated_at.isoformat(),
    }


def _mapping_from_dict(d: dict[str, object]) -> IdentityChannelMappingRecord:
    return IdentityChannelMappingRecord(
        mapping_id=str(d["mapping_id"]),
        connector=str(d["connector"]),
        actor_external_id=str(d["actor_external_id"]),
        guild_id=str(d["guild_id"]),
        channel_id=str(d["channel_id"]),
        channel_type=str(d["channel_type"]),
        status=cast(IdentityChannelStatus, str(d["status"])),
        created_at=datetime.fromisoformat(str(d["created_at"])),
        updated_at=datetime.fromisoformat(str(d["updated_at"])),
    )


# ---------------------------------------------------------------------------
# InMemoryIdempotencyCacheStore
# ---------------------------------------------------------------------------


class InMemoryIdempotencyCacheStore:
    """Test-only in-memory idempotency cache store.

    API matches RedisIdempotencyCacheStore: claim(namespace, key, payload_hash),
    increment_attempt, complete, get, list_namespace.
    """

    def __init__(self, *, snapshot_path: Path | None = None) -> None:
        # key = (namespace, key)
        self._records: dict[tuple[str, str], CacheIdempotencyRecord] = {}
        self._snapshot_path = snapshot_path
        if snapshot_path is not None and snapshot_path.exists():
            self._load_snapshot()

    def claim(
        self,
        *,
        namespace: str,
        key: str,
        payload_hash: str,
    ) -> tuple[str, CacheIdempotencyRecord]:
        """Claim a new record or return existing status (new/in_progress/replay/conflict)."""
        store_key = (namespace, key)
        now = datetime.now(tz=UTC)
        existing = self._records.get(store_key)
        if existing is None:
            record = CacheIdempotencyRecord(
                namespace=namespace,
                key=key,
                payload_hash=payload_hash,
                status=cast(CacheIdempotencyStatus, "in_progress"),
                attempt_count=0,
                result=None,
                created_at=now,
                updated_at=now,
            )
            self._records[store_key] = record
            self._flush_snapshot()
            return "new", record
        if existing.payload_hash != payload_hash:
            return "conflict", existing
        if existing.status == "completed":
            return "replay", existing
        return "in_progress", existing

    def increment_attempt(
        self,
        *,
        namespace: str,
        key: str,
    ) -> CacheIdempotencyRecord | None:
        """Increment attempt_count on an existing record."""
        store_key = (namespace, key)
        existing = self._records.get(store_key)
        if existing is None:
            return None
        now = datetime.now(tz=UTC)
        updated = replace(
            existing,
            attempt_count=existing.attempt_count + 1,
            updated_at=now,
        )
        self._records[store_key] = updated
        self._flush_snapshot()
        return updated

    def complete(
        self,
        *,
        namespace: str,
        key: str,
        result: dict[str, object],
    ) -> CacheIdempotencyRecord | None:
        """Mark record as completed with result payload."""
        store_key = (namespace, key)
        existing = self._records.get(store_key)
        if existing is None:
            return None
        now = datetime.now(tz=UTC)
        result_tuple: tuple[tuple[str, str], ...] = tuple(
            (str(k), str(v)) for k, v in result.items()
        )
        updated = replace(
            existing,
            status=cast(CacheIdempotencyStatus, "completed"),
            result=result_tuple,
            updated_at=now,
        )
        self._records[store_key] = updated
        self._flush_snapshot()
        return updated

    def get(self, *, namespace: str, key: str) -> CacheIdempotencyRecord | None:
        """Retrieve a record by namespace and key."""
        return self._records.get((namespace, key))

    def list_namespace(self, *, namespace: str) -> tuple[CacheIdempotencyRecord, ...]:
        """List all records in a namespace."""
        return tuple(r for (ns, _), r in self._records.items() if ns == namespace)

    # --- legacy API used by older idempotency tests (principal_id / idempotency_key) ---

    def claim_by_principal(
        self,
        principal_id: str,
        idempotency_key: str,
        payload_hash: str,
    ) -> tuple[str, CacheIdempotencyRecord]:
        """Legacy claim API (principal_id + idempotency_key)."""
        return self.claim(
            namespace=principal_id,
            key=idempotency_key,
            payload_hash=payload_hash,
        )

    def bind_task_id(self, principal_id: str, idempotency_key: str, task_id: str) -> None:
        """Legacy bind method for admission-layer compatibility."""
        store_key = (principal_id, idempotency_key)
        existing = self._records.get(store_key)
        if existing is None:
            return
        now = datetime.now(tz=UTC)
        updated = replace(existing, updated_at=now)
        self._records[store_key] = updated
        self._flush_snapshot()

    def _load_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        try:
            payload = json.loads(self._snapshot_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        for raw in payload.get("records", []):
            rec = CacheIdempotencyRecord(
                namespace=str(raw["namespace"]),
                key=str(raw["key"]),
                payload_hash=str(raw["payload_hash"]),
                status=cast(CacheIdempotencyStatus, str(raw.get("status", "in_progress"))),
                attempt_count=int(str(raw.get("attempt_count", 0))),
                result=tuple(
                    (str(pair[0]), str(pair[1]))  # type: ignore[index]
                    for pair in cast(list[object], raw["result"])
                )
                if raw.get("result")
                else None,
                created_at=datetime.fromisoformat(str(raw["created_at"])),
                updated_at=datetime.fromisoformat(str(raw["updated_at"])),
            )
            self._records[(rec.namespace, rec.key)] = rec

    def _flush_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "records": [
                {
                    "namespace": r.namespace,
                    "key": r.key,
                    "payload_hash": r.payload_hash,
                    "status": r.status,
                    "attempt_count": r.attempt_count,
                    "result": [list(p) for p in r.result] if r.result else None,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat(),
                }
                for r in self._records.values()
            ]
        }
        self._snapshot_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# InMemoryAgentRegistryRepository
# ---------------------------------------------------------------------------


class InMemoryAgentRegistryRepository:
    """Test-only in-memory agent registry repository."""

    _INSTITUTIONAL_ROLES = ("administrator", "auditor", "ceo", "cwo", "cso", "secretary")
    _ADVISORY_ONLY_ROLES: frozenset[str] = frozenset({"secretary"})

    def __init__(self) -> None:
        from openqilin.data_access.repositories.agent_registry import (
            AgentRecord,
            AgentRegistryRepositoryError,
        )

        self._agents: dict[str, "AgentRecord"] = {}
        self._AgentRecord = AgentRecord
        self._AgentRegistryRepositoryError = AgentRegistryRepositoryError

    def bootstrap_institutional_agents(self) -> tuple:
        """Ensure canonical institutional agents exist; return active records."""

        now = datetime.now(tz=UTC)
        for role in self._INSTITUTIONAL_ROLES:
            existing = self._agents.get(role)
            if existing is not None and role in self._ADVISORY_ONLY_ROLES:
                if existing.agent_type != "institutional":
                    raise self._AgentRegistryRepositoryError(
                        code="agent_registry_advisory_only_violation",
                        message=(
                            f"Role '{role}' must be registered with advisory-only capability "
                            f"(agent_type='institutional'). "
                            f"Found agent_type='{existing.agent_type}'. "
                            "Secretary cannot be granted command or mutation capabilities."
                        ),
                    )
            if existing is None:
                record = self._AgentRecord(
                    agent_id=f"{role}_core",
                    role=role,
                    agent_type="institutional",
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
                self._agents[role] = record
            elif existing.status != "active":
                self._agents[role] = replace(existing, status="active", updated_at=now)
        return tuple(sorted(self._agents.values(), key=lambda r: r.role))

    def get_agent_by_role(self, role: str) -> object | None:
        return self._agents.get(role.strip().lower())

    def list_agents(self, *, agent_type: str | None = None) -> tuple:
        if agent_type is None:
            return tuple(sorted(self._agents.values(), key=lambda r: r.role))
        return tuple(
            sorted(
                (r for r in self._agents.values() if r.agent_type == agent_type),
                key=lambda r: r.role,
            )
        )


# ---------------------------------------------------------------------------
# InMemoryProjectSpaceBindingRepository
# ---------------------------------------------------------------------------

from openqilin.project_spaces.binding_repository import PostgresProjectSpaceBindingRepository  # noqa: E402
from openqilin.project_spaces.models import BindingState as _BindingState  # noqa: E402
from openqilin.project_spaces.models import ProjectSpaceBinding as _ProjectSpaceBinding  # noqa: E402


class InMemoryProjectSpaceBindingRepository(PostgresProjectSpaceBindingRepository):
    """Test-only in-memory project space binding repository.

    Overrides PostgresProjectSpaceBindingRepository without a real session factory.
    Used by the component test conftest to avoid needing a compose stack.
    """

    def __init__(self) -> None:  # type: ignore[override]
        self._by_channel: dict[tuple[str, str], _ProjectSpaceBinding] = {}
        self._by_project: dict[str, _ProjectSpaceBinding] = {}
        self._by_id: dict[str, _ProjectSpaceBinding] = {}

    def insert(self, binding: _ProjectSpaceBinding) -> _ProjectSpaceBinding:
        self._by_channel[(binding.guild_id, binding.channel_id)] = binding
        self._by_project[binding.project_id] = binding
        self._by_id[binding.id] = binding
        return binding

    def find_by_channel(self, guild_id: str, channel_id: str) -> _ProjectSpaceBinding | None:
        return self._by_channel.get((guild_id, channel_id))

    def find_by_project_id(self, project_id: str) -> _ProjectSpaceBinding | None:
        return self._by_project.get(project_id)

    def update_state(self, binding_id: str, state: _BindingState) -> _ProjectSpaceBinding:
        from dataclasses import replace as dc_replace

        binding = self._by_id[binding_id]
        updated = dc_replace(binding, binding_state=state, updated_at=datetime.now(tz=UTC))
        self._by_id[binding_id] = updated
        self._by_channel[(updated.guild_id, updated.channel_id)] = updated
        self._by_project[updated.project_id] = updated
        return updated
