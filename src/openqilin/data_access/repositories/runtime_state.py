"""Runtime-state repository shell for task admission persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TaskRecord:
    """Persisted task admission state."""

    task_id: str
    request_id: str
    trace_id: str
    principal_id: str
    principal_role: str
    trust_domain: str
    connector: str
    command: str
    target: str
    args: tuple[str, ...]
    metadata: tuple[tuple[str, str], ...]
    project_id: str | None
    idempotency_key: str
    status: str
    created_at: datetime
    outcome_source: str | None = None
    outcome_error_code: str | None = None
    outcome_message: str | None = None
    outcome_details: tuple[tuple[str, str], ...] | None = None
    dispatch_target: str | None = None
    dispatch_id: str | None = None


class RuntimeStateRepositoryError(ValueError):
    """Raised when runtime-state snapshot persistence cannot be completed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def metadata_or_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return []
