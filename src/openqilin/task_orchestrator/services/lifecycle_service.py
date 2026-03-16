"""Task lifecycle transition helpers for M1 orchestrator path."""

from __future__ import annotations

from openqilin.data_access.repositories.runtime_state import (
    InMemoryRuntimeStateRepository,
    TaskRecord,
)


class TaskLifecycleService:
    """Apply lifecycle status transitions to runtime-state records."""

    def __init__(self, runtime_state_repo: InMemoryRuntimeStateRepository) -> None:
        self._runtime_state_repo = runtime_state_repo

    def mark_dispatched(
        self,
        task_id: str,
        *,
        dispatch_target: str,
        dispatch_id: str,
        message: str,
    ) -> TaskRecord | None:
        """Mark task as dispatched after dispatch-accept."""

        return self._runtime_state_repo.update_task_status(
            task_id,
            "dispatched",
            outcome_source=f"dispatch_{dispatch_target}",
            outcome_error_code=None,
            outcome_message=message,
            dispatch_target=dispatch_target,
            dispatch_id=dispatch_id,
        )

    def mark_blocked_dispatch(
        self,
        task_id: str,
        *,
        error_code: str | None,
        message: str,
        dispatch_target: str,
        outcome_source: str = "dispatch_sandbox_adapter",
    ) -> TaskRecord | None:
        """Mark task as blocked due to dispatch boundary failure."""

        return self._runtime_state_repo.update_task_status(
            task_id,
            "blocked",
            outcome_source=outcome_source,
            outcome_error_code=error_code,
            outcome_message=message,
            dispatch_target=dispatch_target,
            dispatch_id=None,
        )

    def mark_failed(
        self,
        task_id: str,
        *,
        error_code: str,
        message: str,
        outcome_source: str,
    ) -> TaskRecord | None:
        """Mark task as failed due to an unrecoverable error."""

        return self._runtime_state_repo.update_task_status(
            task_id,
            "failed",
            outcome_source=outcome_source,
            outcome_error_code=error_code,
            outcome_message=message,
        )
