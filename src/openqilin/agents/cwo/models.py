"""CWO agent request/response models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CwoRequest:
    """Workforce command request routed to the CWO agent."""

    message: str
    intent: str
    project_id: str | None
    context: dict[str, Any]
    trace_id: str


@dataclass(frozen=True, slots=True)
class CwoResponse:
    """CWO response carrying a workforce command or governed status."""

    action_taken: str | None
    advisory_text: str
    workforce_status: str | None
    trace_id: str


class CwoCommandError(PermissionError):
    """Raised when a CWO command action is blocked."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "cwo_command_denied"


class CwoApprovalChainError(PermissionError):
    """Raised when workforce initialization lacks the required approval chain."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "cwo_approval_chain_incomplete"
