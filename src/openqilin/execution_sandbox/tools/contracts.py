"""Common contracts for governed tool invocation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

ToolDecision = Literal["ok", "denied"]


@dataclass(frozen=True, slots=True)
class ToolCallContext:
    """Invocation context used by governed tool services."""

    task_id: str
    request_id: str
    trace_id: str
    principal_id: str
    recipient_role: str
    recipient_id: str | None
    project_id: str | None


@dataclass(frozen=True, slots=True)
class ToolSourceDescriptor:
    """Citation-ready source metadata returned by one governed tool call."""

    source_id: str
    source_kind: str
    version: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Normalized tool call result envelope."""

    decision: ToolDecision
    tool_name: str
    tool_call_id: str
    trace_id: str
    request_id: str
    data: Mapping[str, object] | None
    sources: tuple[ToolSourceDescriptor, ...]
    error_code: str | None = None
    message: str = ""
