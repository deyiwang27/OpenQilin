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

    def mark_dispatched(self, task_id: str) -> TaskRecord | None:
        """Mark task as dispatched after dispatch-accept."""

        return self._runtime_state_repo.update_task_status(task_id, "dispatched")

    def mark_blocked_dispatch(self, task_id: str) -> TaskRecord | None:
        """Mark task as blocked due to dispatch boundary failure."""

        return self._runtime_state_repo.update_task_status(task_id, "blocked_dispatch")
