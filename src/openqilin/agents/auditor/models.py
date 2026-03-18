"""Auditor agent request/response models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuditorRequest:
    """Oversight event routed to the auditor agent."""

    event_type: str
    task_id: str | None
    project_id: str | None
    severity: str
    rule_ids: tuple[str, ...]
    rationale: str
    source_agent_role: str | None
    trace_id: str


@dataclass(frozen=True, slots=True)
class AuditorResponse:
    """Oversight outcome returned by the auditor agent."""

    action_taken: str | None
    finding_id: str | None
    advisory_text: str
    trace_id: str


class AuditorFindingError(RuntimeError):
    """Raised when a finding record cannot be written."""
