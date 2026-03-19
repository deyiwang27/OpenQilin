"""Specialist agent request/response models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpecialistRequest:
    """Task execution request dispatched by Project Manager."""

    task_id: str
    project_id: str
    task_description: str
    approved_tools: tuple[str, ...]
    dispatch_source_role: str
    trace_id: str


@dataclass(frozen=True, slots=True)
class SpecialistResponse:
    """Specialist execution outcome."""

    execution_status: str
    output_text: str
    artifact_id: str | None
    blocker: str | None
    trace_id: str


class SpecialistDispatchAuthError(PermissionError):
    """Raised when a request is received from a non-PM dispatch source."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "specialist_dispatch_auth_required"


class ToolNotAuthorizedError(PermissionError):
    """Raised when a task requests a tool not in the approved_tools list."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"tool not authorized: {tool_name!r}")
        self.code = "specialist_tool_not_authorized"
        self.tool_name = tool_name
