"""PostgreSQL-backed project repository replacing InMemoryGovernanceRepository.

Projects are stored as document-style JSONB state, preserving all governance invariants
in Python while using PostgreSQL for durable persistence across restarts.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Mapping
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from openqilin.control_plane.governance.project_lifecycle import (
    ProjectLifecycleError,
    assert_project_transition,
    parse_project_status,
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


class PostgresProjectRepository:
    """PostgreSQL-backed governance project repository.

    Uses JSONB document storage for the full project aggregate, preserving all
    lifecycle invariants in Python. Suitable for MVP-scale project counts.
    """

    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    # --- read methods --------------------------------------------------------

    def get_project(self, project_id: str) -> ProjectRecord | None:
        """Load one project by identifier."""

        with self._session_factory() as session:
            row = (
                session.execute(
                    text("SELECT * FROM projects WHERE project_id = :project_id"),
                    {"project_id": project_id},
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return _project_from_row(dict(row))

    def list_projects(self) -> tuple[ProjectRecord, ...]:
        """List all projects sorted by creation timestamp and id."""

        with self._session_factory() as session:
            rows = (
                session.execute(
                    text("SELECT * FROM projects ORDER BY created_at ASC, project_id ASC")
                )
                .mappings()
                .all()
            )
        return tuple(_project_from_row(dict(row)) for row in rows)

    # --- write methods -------------------------------------------------------

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
        candidate_id = project_id or str(uuid4())
        if self.get_project(candidate_id) is not None:
            raise GovernanceRepositoryError(
                code="governance_project_exists",
                message=f"project already exists: {candidate_id}",
            )
        timestamp = datetime.now(tz=UTC)
        project = ProjectRecord(
            project_id=candidate_id,
            name=name.strip(),
            objective=objective.strip(),
            status=normalized_status,
            created_at=timestamp,
            updated_at=timestamp,
            metadata=(
                tuple(sorted((str(k), str(v)) for k, v in metadata.items()))
                if metadata is not None
                else ()
            ),
        )
        self._upsert_project(project)
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
        """Apply one lifecycle transition using canonical project-state guards."""

        from dataclasses import replace

        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        try:
            normalized_next = assert_project_transition(project.status, next_status)
        except ProjectLifecycleError as error:
            raise GovernanceRepositoryError(code=error.code, message=error.message) from error
        if normalized_next == "completed":
            _assert_completion_transition_allowed(project=project, actor_role=actor_role)

        transition = ProjectStatusTransitionRecord(
            project_id=project.project_id,
            from_status=project.status,
            to_status=normalized_next,
            reason_code=reason_code.strip(),
            actor_role=actor_role.strip(),
            trace_id=trace_id.strip(),
            timestamp=datetime.now(tz=UTC),
            metadata=(
                tuple(sorted((str(k), str(v)) for k, v in metadata.items()))
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
        self._upsert_project(updated)
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

        from dataclasses import replace

        project = self.get_project(project_id)
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
        self._upsert_project(updated)
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

        from dataclasses import replace

        normalized_role = actor_role.strip()
        project = self.get_project(project_id)
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
            (a for a in project.proposal_approvals if a.actor_role == normalized_role),
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
        self._upsert_project(updated)
        if _has_triad_approvals(updated):
            promoted = self.transition_project_status(
                project_id=project_id,
                next_status="approved",
                reason_code="proposal_triad_approved",
                actor_role=normalized_role,
                trace_id=trace_id,
            )
            return promoted, True
        return updated, True

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
        """Persist one completion report for an active project."""

        from dataclasses import replace

        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        if project.status != "active":
            raise GovernanceRepositoryError(
                code="governance_project_not_active",
                message="completion report requires active project status",
            )
        normalized_actor_role = actor_role.strip().lower()
        if normalized_actor_role != "project_manager":
            raise GovernanceRepositoryError(
                code="governance_project_completion_report_role_forbidden",
                message="completion report submission is limited to project_manager",
            )
        if project.completion_report is not None:
            raise GovernanceRepositoryError(
                code="governance_project_completion_report_exists",
                message="completion report already exists for project",
            )
        report = CompletionReportRecord(
            report_id=str(uuid4()),
            project_id=project_id,
            actor_id=actor_id.strip(),
            actor_role=normalized_actor_role,
            summary=summary.strip(),
            metric_results=(
                tuple(sorted((str(k), str(v)) for k, v in metric_results.items()))
                if metric_results is not None
                else ()
            ),
            trace_id=trace_id.strip(),
            completion_report_storage_uri=None,
            completion_report_content_hash=None,
            timestamp=datetime.now(tz=UTC),
        )
        updated = replace(project, updated_at=report.timestamp, completion_report=report)
        self._upsert_project(updated)
        return report

    def record_completion_approval(
        self,
        *,
        project_id: str,
        actor_id: str,
        actor_role: str,
        trace_id: str,
    ) -> tuple[ProjectRecord, bool]:
        """Persist completion approval; auto-finalize when both CEO and CWO have approved."""

        from dataclasses import replace

        normalized_role = actor_role.strip().lower()
        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        if project.status != "active":
            raise GovernanceRepositoryError(
                code="governance_project_not_active",
                message="completion approvals require active project status",
            )
        if project.completion_report is None:
            raise GovernanceRepositoryError(
                code="governance_project_completion_report_missing",
                message="completion report must be submitted before approval",
            )
        existing = next(
            (a for a in project.completion_approvals if a.actor_role == normalized_role),
            None,
        )
        if existing is not None and existing.actor_id == actor_id.strip():
            return project, False
        if existing is not None and existing.actor_id != actor_id.strip():
            raise GovernanceRepositoryError(
                code="governance_approval_role_conflict",
                message=f"completion role already approved by another actor: {normalized_role}",
            )
        approval = CompletionApprovalRecord(
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
            completion_approvals=project.completion_approvals + (approval,),
        )
        self._upsert_project(updated)
        if _has_completion_approvals(updated):
            return updated, True
        return updated, True

    def record_completion_owner_notified(
        self,
        *,
        project_id: str,
        trace_id: str,
    ) -> ProjectRecord:
        """Record that the owner was notified of project completion approval."""

        from dataclasses import replace

        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        now = datetime.now(tz=UTC)
        updated = replace(
            project,
            updated_at=now,
            completion_owner_notified_at=now,
            completion_owner_notification_trace_id=trace_id.strip(),
        )
        self._upsert_project(updated)
        return updated

    def record_initialization(
        self,
        *,
        project_id: str,
        snapshot: ProjectInitializationSnapshot,
    ) -> ProjectRecord:
        """Persist CWO initialization charter for a project."""

        from dataclasses import replace

        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        updated = replace(
            project,
            updated_at=datetime.now(tz=UTC),
            initialization=snapshot,
        )
        self._upsert_project(updated)
        return updated

    def bind_workforce(
        self,
        *,
        project_id: str,
        binding: WorkforceBindingRecord,
    ) -> ProjectRecord:
        """Append one workforce binding to a project."""

        from dataclasses import replace

        project = self.get_project(project_id)
        if project is None:
            raise GovernanceRepositoryError(
                code="governance_project_missing",
                message=f"project not found: {project_id}",
            )
        updated = replace(
            project,
            updated_at=datetime.now(tz=UTC),
            workforce_bindings=project.workforce_bindings + (binding,),
        )
        self._upsert_project(updated)
        return updated

    # --- internal helpers ----------------------------------------------------

    def _upsert_project(self, project: ProjectRecord) -> None:
        """Insert or replace the full project document."""

        row = _project_to_row(project)
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO projects (
                        project_id, name, objective, status, metadata,
                        transitions, proposal_messages, proposal_approvals,
                        completion_report, completion_approvals,
                        completion_owner_notified_at,
                        completion_owner_notification_trace_id,
                        initialization, workforce_bindings,
                        created_at, updated_at
                    ) VALUES (
                        :project_id, :name, :objective, :status, CAST(:metadata AS JSONB),
                        CAST(:transitions AS JSONB), CAST(:proposal_messages AS JSONB), CAST(:proposal_approvals AS JSONB),
                        CAST(:completion_report AS JSONB), CAST(:completion_approvals AS JSONB),
                        :completion_owner_notified_at,
                        :completion_owner_notification_trace_id,
                        CAST(:initialization AS JSONB), CAST(:workforce_bindings AS JSONB),
                        :created_at, :updated_at
                    )
                    ON CONFLICT (project_id) DO UPDATE SET
                        name                                    = EXCLUDED.name,
                        objective                               = EXCLUDED.objective,
                        status                                  = EXCLUDED.status,
                        metadata                                = EXCLUDED.metadata,
                        transitions                             = EXCLUDED.transitions,
                        proposal_messages                       = EXCLUDED.proposal_messages,
                        proposal_approvals                      = EXCLUDED.proposal_approvals,
                        completion_report                       = EXCLUDED.completion_report,
                        completion_approvals                    = EXCLUDED.completion_approvals,
                        completion_owner_notified_at            = EXCLUDED.completion_owner_notified_at,
                        completion_owner_notification_trace_id  = EXCLUDED.completion_owner_notification_trace_id,
                        initialization                          = EXCLUDED.initialization,
                        workforce_bindings                      = EXCLUDED.workforce_bindings,
                        updated_at                              = EXCLUDED.updated_at
                    """
                ),
                row,
            )
            session.commit()


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _assert_completion_transition_allowed(*, project: ProjectRecord, actor_role: str) -> None:
    normalized_role = actor_role.strip().lower()
    if normalized_role not in {"ceo", "cwo"}:
        raise GovernanceRepositoryError(
            code="governance_project_completion_role_forbidden",
            message="completion finalization is limited to ceo or cwo",
        )
    if project.completion_report is None:
        raise GovernanceRepositoryError(
            code="governance_project_completion_report_missing",
            message="project completion report is required before completion transition",
        )
    approval_roles = {a.actor_role for a in project.completion_approvals}
    missing_roles = tuple(sorted({"ceo", "cwo"} - approval_roles))
    if missing_roles:
        raise GovernanceRepositoryError(
            code="governance_project_completion_approval_missing",
            message="project completion approvals are missing for roles: "
            + ",".join(missing_roles),
        )
    if project.completion_owner_notified_at is None:
        raise GovernanceRepositoryError(
            code="governance_project_completion_owner_notification_missing",
            message="owner notification must be recorded before completion transition",
        )


def _has_triad_approvals(project: ProjectRecord) -> bool:
    roles = {a.actor_role for a in project.proposal_approvals}
    return {"owner", "ceo", "cwo"}.issubset(roles)


def _has_completion_approvals(project: ProjectRecord) -> bool:
    roles = {a.actor_role for a in project.completion_approvals}
    return {"ceo", "cwo"}.issubset(roles)


def _dt_to_iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _dt_from_iso(value: str | None | object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        return datetime.fromisoformat(value).astimezone(UTC)
    if hasattr(value, "tzinfo"):
        if value.tzinfo is None:  # type: ignore[attr-defined]
            return value.replace(tzinfo=UTC)  # type: ignore[attr-defined, return-value]
        return value  # type: ignore[return-value]
    return None


def _transition_to_dict(t: ProjectStatusTransitionRecord) -> dict[str, object]:
    return {
        "project_id": t.project_id,
        "from_status": t.from_status,
        "to_status": t.to_status,
        "reason_code": t.reason_code,
        "actor_role": t.actor_role,
        "trace_id": t.trace_id,
        "timestamp": _dt_to_iso(t.timestamp),
        "metadata": list(t.metadata),
    }


def _transition_from_dict(d: dict[str, object]) -> ProjectStatusTransitionRecord:
    return ProjectStatusTransitionRecord(
        project_id=str(d["project_id"]),
        from_status=str(d["from_status"]),  # type: ignore[arg-type]
        to_status=str(d["to_status"]),  # type: ignore[arg-type]
        reason_code=str(d["reason_code"]),
        actor_role=str(d["actor_role"]),
        trace_id=str(d["trace_id"]),
        timestamp=_dt_from_iso(d.get("timestamp")),  # type: ignore[arg-type]
        metadata=tuple(
            (str(item[0]), str(item[1]))
            for item in (d.get("metadata") or [])  # type: ignore[attr-defined]
            if isinstance(item, (list, tuple)) and len(item) == 2
        ),
    )


def _proposal_message_to_dict(m: ProposalMessageRecord) -> dict[str, object]:
    return {
        "message_id": m.message_id,
        "project_id": m.project_id,
        "actor_id": m.actor_id,
        "actor_role": m.actor_role,
        "content": m.content,
        "trace_id": m.trace_id,
        "timestamp": _dt_to_iso(m.timestamp),
    }


def _proposal_message_from_dict(d: dict[str, object]) -> ProposalMessageRecord:
    return ProposalMessageRecord(
        message_id=str(d["message_id"]),
        project_id=str(d["project_id"]),
        actor_id=str(d["actor_id"]),
        actor_role=str(d["actor_role"]),
        content=str(d["content"]),
        trace_id=str(d["trace_id"]),
        timestamp=_dt_from_iso(d.get("timestamp")),  # type: ignore[arg-type]
    )


def _proposal_approval_to_dict(a: ProposalApprovalRecord) -> dict[str, object]:
    return {
        "approval_id": a.approval_id,
        "project_id": a.project_id,
        "actor_id": a.actor_id,
        "actor_role": a.actor_role,
        "trace_id": a.trace_id,
        "timestamp": _dt_to_iso(a.timestamp),
    }


def _proposal_approval_from_dict(d: dict[str, object]) -> ProposalApprovalRecord:
    return ProposalApprovalRecord(
        approval_id=str(d["approval_id"]),
        project_id=str(d["project_id"]),
        actor_id=str(d["actor_id"]),
        actor_role=str(d["actor_role"]),
        trace_id=str(d["trace_id"]),
        timestamp=_dt_from_iso(d.get("timestamp")),  # type: ignore[arg-type]
    )


def _completion_report_to_dict(r: CompletionReportRecord) -> dict[str, object]:
    return {
        "report_id": r.report_id,
        "project_id": r.project_id,
        "actor_id": r.actor_id,
        "actor_role": r.actor_role,
        "summary": r.summary,
        "metric_results": list(r.metric_results),
        "trace_id": r.trace_id,
        "completion_report_storage_uri": r.completion_report_storage_uri,
        "completion_report_content_hash": r.completion_report_content_hash,
        "timestamp": _dt_to_iso(r.timestamp),
    }


def _completion_report_from_dict(d: dict[str, object]) -> CompletionReportRecord:
    return CompletionReportRecord(
        report_id=str(d["report_id"]),
        project_id=str(d["project_id"]),
        actor_id=str(d["actor_id"]),
        actor_role=str(d["actor_role"]),
        summary=str(d["summary"]),
        metric_results=tuple(
            (str(item[0]), str(item[1]))
            for item in (d.get("metric_results") or [])  # type: ignore[attr-defined]
            if isinstance(item, (list, tuple)) and len(item) == 2
        ),
        trace_id=str(d["trace_id"]),
        completion_report_storage_uri=(
            str(d["completion_report_storage_uri"])
            if d.get("completion_report_storage_uri")
            else None
        ),
        completion_report_content_hash=(
            str(d["completion_report_content_hash"])
            if d.get("completion_report_content_hash")
            else None
        ),
        timestamp=_dt_from_iso(d.get("timestamp")),  # type: ignore[arg-type]
    )


def _completion_approval_to_dict(a: CompletionApprovalRecord) -> dict[str, object]:
    return {
        "approval_id": a.approval_id,
        "project_id": a.project_id,
        "actor_id": a.actor_id,
        "actor_role": a.actor_role,
        "trace_id": a.trace_id,
        "timestamp": _dt_to_iso(a.timestamp),
    }


def _completion_approval_from_dict(d: dict[str, object]) -> CompletionApprovalRecord:
    return CompletionApprovalRecord(
        approval_id=str(d["approval_id"]),
        project_id=str(d["project_id"]),
        actor_id=str(d["actor_id"]),
        actor_role=str(d["actor_role"]),
        trace_id=str(d["trace_id"]),
        timestamp=_dt_from_iso(d.get("timestamp")),  # type: ignore[arg-type]
    )


def _initialization_to_dict(s: ProjectInitializationSnapshot) -> dict[str, object]:
    return {
        "objective": s.objective,
        "budget_currency_total": s.budget_currency_total,
        "budget_quota_total": s.budget_quota_total,
        "metric_plan": list(s.metric_plan),
        "workforce_plan": list(s.workforce_plan),
        "actor_id": s.actor_id,
        "actor_role": s.actor_role,
        "trace_id": s.trace_id,
        "charter_storage_uri": s.charter_storage_uri,
        "charter_content_hash": s.charter_content_hash,
        "scope_statement_storage_uri": s.scope_statement_storage_uri,
        "scope_statement_content_hash": s.scope_statement_content_hash,
        "budget_plan_storage_uri": s.budget_plan_storage_uri,
        "budget_plan_content_hash": s.budget_plan_content_hash,
        "metric_plan_storage_uri": s.metric_plan_storage_uri,
        "metric_plan_content_hash": s.metric_plan_content_hash,
        "workforce_plan_storage_uri": s.workforce_plan_storage_uri,
        "workforce_plan_content_hash": s.workforce_plan_content_hash,
        "execution_plan_storage_uri": s.execution_plan_storage_uri,
        "execution_plan_content_hash": s.execution_plan_content_hash,
        "initialized_at": _dt_to_iso(s.initialized_at),
    }


def _initialization_from_dict(d: dict[str, object]) -> ProjectInitializationSnapshot:
    def _pair_list(v: object) -> tuple[tuple[str, str], ...]:
        lst = v if isinstance(v, list) else []
        return tuple(
            (str(item[0]), str(item[1]))
            for item in lst
            if isinstance(item, (list, tuple)) and len(item) == 2
        )

    return ProjectInitializationSnapshot(
        objective=str(d["objective"]),
        budget_currency_total=float(d.get("budget_currency_total", 0.0)),  # type: ignore[arg-type]
        budget_quota_total=float(d.get("budget_quota_total", 0.0)),  # type: ignore[arg-type]
        metric_plan=_pair_list(d.get("metric_plan")),
        workforce_plan=_pair_list(d.get("workforce_plan")),
        actor_id=str(d["actor_id"]),
        actor_role=str(d["actor_role"]),
        trace_id=str(d["trace_id"]),
        charter_storage_uri=str(d["charter_storage_uri"]) if d.get("charter_storage_uri") else None,
        charter_content_hash=str(d["charter_content_hash"])
        if d.get("charter_content_hash")
        else None,
        scope_statement_storage_uri=str(d["scope_statement_storage_uri"])
        if d.get("scope_statement_storage_uri")
        else None,
        scope_statement_content_hash=str(d["scope_statement_content_hash"])
        if d.get("scope_statement_content_hash")
        else None,
        budget_plan_storage_uri=str(d["budget_plan_storage_uri"])
        if d.get("budget_plan_storage_uri")
        else None,
        budget_plan_content_hash=str(d["budget_plan_content_hash"])
        if d.get("budget_plan_content_hash")
        else None,
        metric_plan_storage_uri=str(d["metric_plan_storage_uri"])
        if d.get("metric_plan_storage_uri")
        else None,
        metric_plan_content_hash=str(d["metric_plan_content_hash"])
        if d.get("metric_plan_content_hash")
        else None,
        workforce_plan_storage_uri=str(d["workforce_plan_storage_uri"])
        if d.get("workforce_plan_storage_uri")
        else None,
        workforce_plan_content_hash=str(d["workforce_plan_content_hash"])
        if d.get("workforce_plan_content_hash")
        else None,
        execution_plan_storage_uri=str(d["execution_plan_storage_uri"])
        if d.get("execution_plan_storage_uri")
        else None,
        execution_plan_content_hash=str(d["execution_plan_content_hash"])
        if d.get("execution_plan_content_hash")
        else None,
        initialized_at=_dt_from_iso(d.get("initialized_at")),  # type: ignore[arg-type]
    )


def _workforce_binding_to_dict(b: WorkforceBindingRecord) -> dict[str, object]:
    return {
        "binding_id": b.binding_id,
        "project_id": b.project_id,
        "role": b.role,
        "template_id": b.template_id,
        "llm_routing_profile": b.llm_routing_profile,
        "system_prompt_hash": b.system_prompt_hash,
        "mandatory_operations": list(b.mandatory_operations),
        "binding_status": b.binding_status,
        "actor_id": b.actor_id,
        "actor_role": b.actor_role,
        "trace_id": b.trace_id,
        "created_at": _dt_to_iso(b.created_at),
    }


def _workforce_binding_from_dict(d: dict[str, object]) -> WorkforceBindingRecord:
    return WorkforceBindingRecord(
        binding_id=str(d["binding_id"]),
        project_id=str(d["project_id"]),
        role=str(d["role"]),
        template_id=str(d["template_id"]),
        llm_routing_profile=str(d["llm_routing_profile"]),
        system_prompt_hash=str(d["system_prompt_hash"]),
        mandatory_operations=tuple(str(op) for op in (d.get("mandatory_operations") or [])),  # type: ignore[attr-defined]
        binding_status=str(d["binding_status"]),
        actor_id=str(d["actor_id"]),
        actor_role=str(d["actor_role"]),
        trace_id=str(d["trace_id"]),
        created_at=_dt_from_iso(d.get("created_at")),  # type: ignore[arg-type]
    )


def _project_to_row(project: ProjectRecord) -> dict[str, object]:
    return {
        "project_id": project.project_id,
        "name": project.name,
        "objective": project.objective,
        "status": project.status,
        "metadata": json.dumps(list(project.metadata)),
        "transitions": json.dumps([_transition_to_dict(t) for t in project.transitions]),
        "proposal_messages": json.dumps(
            [_proposal_message_to_dict(m) for m in project.proposal_messages]
        ),
        "proposal_approvals": json.dumps(
            [_proposal_approval_to_dict(a) for a in project.proposal_approvals]
        ),
        "completion_report": json.dumps(_completion_report_to_dict(project.completion_report))
        if project.completion_report
        else None,
        "completion_approvals": json.dumps(
            [_completion_approval_to_dict(a) for a in project.completion_approvals]
        ),
        "completion_owner_notified_at": project.completion_owner_notified_at,
        "completion_owner_notification_trace_id": project.completion_owner_notification_trace_id,
        "initialization": json.dumps(_initialization_to_dict(project.initialization))
        if project.initialization
        else None,
        "workforce_bindings": json.dumps(
            [_workforce_binding_to_dict(b) for b in project.workforce_bindings]
        ),
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def _parse_jsonb(value: object) -> object:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _project_from_row(row: dict[str, object]) -> ProjectRecord:
    transitions_raw = _parse_jsonb(row.get("transitions") or "[]")
    proposal_messages_raw = _parse_jsonb(row.get("proposal_messages") or "[]")
    proposal_approvals_raw = _parse_jsonb(row.get("proposal_approvals") or "[]")
    completion_report_raw = _parse_jsonb(row.get("completion_report"))
    completion_approvals_raw = _parse_jsonb(row.get("completion_approvals") or "[]")
    initialization_raw = _parse_jsonb(row.get("initialization"))
    workforce_bindings_raw = _parse_jsonb(row.get("workforce_bindings") or "[]")
    metadata_raw = _parse_jsonb(row.get("metadata") or "[]")

    return ProjectRecord(
        project_id=str(row["project_id"]),
        name=str(row["name"]),
        objective=str(row["objective"]),
        status=parse_project_status(str(row["status"])),
        created_at=_dt_from_iso(row["created_at"]),  # type: ignore[arg-type]
        updated_at=_dt_from_iso(row["updated_at"]),  # type: ignore[arg-type]
        metadata=tuple(
            (str(item[0]), str(item[1]))
            for item in (metadata_raw if isinstance(metadata_raw, list) else [])
            if isinstance(item, (list, tuple)) and len(item) == 2
        ),
        transitions=tuple(
            _transition_from_dict(t)
            for t in (transitions_raw if isinstance(transitions_raw, list) else [])
        ),
        proposal_messages=tuple(
            _proposal_message_from_dict(m)
            for m in (proposal_messages_raw if isinstance(proposal_messages_raw, list) else [])
        ),
        proposal_approvals=tuple(
            _proposal_approval_from_dict(a)
            for a in (proposal_approvals_raw if isinstance(proposal_approvals_raw, list) else [])
        ),
        completion_report=(
            _completion_report_from_dict(completion_report_raw)  # type: ignore[arg-type]
            if isinstance(completion_report_raw, dict)
            else None
        ),
        completion_approvals=tuple(
            _completion_approval_from_dict(a)
            for a in (
                completion_approvals_raw if isinstance(completion_approvals_raw, list) else []
            )
        ),
        completion_owner_notified_at=_dt_from_iso(row.get("completion_owner_notified_at")),
        completion_owner_notification_trace_id=(
            str(row["completion_owner_notification_trace_id"])
            if row.get("completion_owner_notification_trace_id")
            else None
        ),
        initialization=(
            _initialization_from_dict(initialization_raw)  # type: ignore[arg-type]
            if isinstance(initialization_raw, dict)
            else None
        ),
        workforce_bindings=tuple(
            _workforce_binding_from_dict(b)
            for b in (workforce_bindings_raw if isinstance(workforce_bindings_raw, list) else [])
        ),
    )
