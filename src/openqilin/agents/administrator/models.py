"""Administrator agent request/response models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdministratorRequest:
    """Infrastructure or document-policy action routed to the administrator."""

    action: str
    project_id: str | None
    agent_id: str | None
    artifact_type: str | None
    reason: str
    severity: str
    rule_ids: tuple[str, ...]
    trace_id: str


@dataclass(frozen=True, slots=True)
class AdministratorResponse:
    """Outcome returned by the administrator agent."""

    action_taken: str
    audit_record_id: str | None
    oversight_text: str
    trace_id: str


class AdministratorError(RuntimeError):
    """Raised when an administrator action cannot be completed."""
