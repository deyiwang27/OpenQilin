"""Task execution result repository contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class TaskExecutionResult:
    """Immutable record of a specialist task execution outcome."""

    result_id: str
    task_id: str
    specialist_agent_id: str
    output_text: str
    tools_used: tuple[str, ...]
    execution_status: str
    trace_id: str
    created_at: datetime


@runtime_checkable
class TaskExecutionResultsRepository(Protocol):
    """Persistence contract for specialist task execution results."""

    def write_result(self, result: TaskExecutionResult) -> TaskExecutionResult:
        """Persist a task execution result."""
        ...

    def get_results_for_task(self, task_id: str) -> tuple[TaskExecutionResult, ...]:
        """Return all results for the given task_id, ordered by created_at ascending."""
        ...


class InProcessTaskExecutionResultsRepository:
    """In-process implementation for single-process MVP deployments."""

    def __init__(self) -> None:
        self._results: list[TaskExecutionResult] = []

    def write_result(self, result: TaskExecutionResult) -> TaskExecutionResult:
        self._results.append(result)
        return result

    def get_results_for_task(self, task_id: str) -> tuple[TaskExecutionResult, ...]:
        return tuple(result for result in self._results if result.task_id == task_id)
