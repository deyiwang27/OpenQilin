"""Project Manager request/response models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ProjectManagerRequest:
    """Project-scoped request routed to the Project Manager agent."""

    message: str
    intent: str
    project_id: str
    context: dict[str, Any]
    trace_id: str


@dataclass(frozen=True, slots=True)
class ProjectManagerResponse:
    """Project Manager response carrying a directive or status decision."""

    advisory_text: str
    action_taken: str | None
    routing_hint: str | None
    artifact_updated: bool
    trace_id: str


class PMProjectContextError(ValueError):
    """Raised when project_id is absent or project state disallows the operation."""

    def __init__(self, message: str = "Project Manager requires a non-empty project_id") -> None:
        super().__init__(message)
        self.code = "pm_project_context_required"


class PMWriteNotAllowedError(PermissionError):
    """Raised when a write is attempted outside the PM write contract."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "pm_write_not_allowed"
