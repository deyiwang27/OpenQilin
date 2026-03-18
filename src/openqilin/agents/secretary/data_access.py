"""Secretary agent data access service.

Provides read-only access to project snapshot, task runtime context, and dashboard
summary so that the SecretaryAgent can include live context in advisory responses.

All methods are read-only. Secretary MUST NOT write project or governance records.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from openqilin.data_access.repositories.postgres.project_repository import (
    PostgresProjectRepository,
)
from openqilin.data_access.repositories.postgres.task_repository import PostgresTaskRepository

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProjectSnapshot:
    """Live project state summary for secretary advisory context."""

    project_id: str
    status: str
    title: str | None
    active_task_count: int
    blocked_task_count: int


@dataclass(frozen=True, slots=True)
class TaskRuntimeContext:
    """Live task state for secretary advisory context."""

    task_id: str
    status: str
    principal_id: str
    trace_id: str
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    """High-level dashboard metrics for secretary advisory context."""

    total_project_count: int
    active_task_count: int
    blocked_task_count: int
    failed_task_count: int


class SecretaryDataAccessService:
    """Read-only data access service for the Secretary agent.

    Provides project snapshot, task runtime context, and dashboard summary
    from PostgreSQL. All reads are fail-soft: exceptions are logged and a
    ``None`` result (or empty summary) is returned to avoid blocking advisory.
    """

    def __init__(
        self,
        *,
        governance_repo: PostgresProjectRepository,
        runtime_state_repo: PostgresTaskRepository,
    ) -> None:
        self._governance_repo = governance_repo
        self._runtime_state_repo = runtime_state_repo

    def get_project_snapshot(self, project_id: str) -> ProjectSnapshot | None:
        """Read project status, task counts, and title from PostgreSQL.

        Returns ``None`` if the project is not found or on read error.
        """
        try:
            project = self._governance_repo.get_project(project_id)
            if project is None:
                return None
            tasks = self._runtime_state_repo.list_tasks()
            project_tasks = [t for t in tasks if t.project_id == project_id]
            active_count = sum(
                1 for t in project_tasks if t.status in ("queued", "running", "dispatched")
            )
            blocked_count = sum(1 for t in project_tasks if t.status == "blocked")
            return ProjectSnapshot(
                project_id=project_id,
                status=project.status,
                title=getattr(project, "title", None),
                active_task_count=active_count,
                blocked_task_count=blocked_count,
            )
        except Exception as exc:
            LOGGER.warning(
                "secretary.data_access.project_snapshot_failed",
                extra={"project_id": project_id, "exc": str(exc)},
            )
            return None

    def get_task_runtime_context(self, task_id: str) -> TaskRuntimeContext | None:
        """Read task state, principal, and error context from PostgreSQL.

        Returns ``None`` if the task is not found or on read error.
        """
        try:
            task = self._runtime_state_repo.get_task_by_id(task_id)
            if task is None:
                return None
            return TaskRuntimeContext(
                task_id=task.task_id,
                status=task.status,
                principal_id=task.principal_id,
                trace_id=task.trace_id,
                error_code=task.outcome_error_code,
            )
        except Exception as exc:
            LOGGER.warning(
                "secretary.data_access.task_context_failed",
                extra={"task_id": task_id, "exc": str(exc)},
            )
            return None

    def get_dashboard_summary(self) -> DashboardSummary:
        """Read aggregate task and project counts for dashboard context.

        Returns zeroed summary on read error (fail-soft: advisory must not block).
        """
        try:
            tasks = self._runtime_state_repo.list_tasks()
            project_ids: set[str] = set()
            active = blocked = failed = 0
            for task in tasks:
                if task.project_id:
                    project_ids.add(task.project_id)
                if task.status in ("queued", "running", "dispatched"):
                    active += 1
                elif task.status == "blocked":
                    blocked += 1
                elif task.status == "failed":
                    failed += 1
            return DashboardSummary(
                total_project_count=len(project_ids),
                active_task_count=active,
                blocked_task_count=blocked,
                failed_task_count=failed,
            )
        except Exception as exc:
            LOGGER.warning(
                "secretary.data_access.dashboard_summary_failed",
                extra={"exc": str(exc)},
            )
            return DashboardSummary(
                total_project_count=0,
                active_task_count=0,
                blocked_task_count=0,
                failed_task_count=0,
            )
