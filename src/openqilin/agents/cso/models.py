"""CSO agent request/response models."""

from __future__ import annotations

from dataclasses import dataclass

from openqilin.control_plane.grammar.models import ChatContext, IntentClass


@dataclass(frozen=True, slots=True)
class CSORequest:
    """Governance advisory request routed to the CSO agent."""

    message: str
    intent: IntentClass
    context: ChatContext
    principal_role: str
    trace_id: str


@dataclass(frozen=True, slots=True)
class CSOResponse:
    """Advisory governance response from the CSO agent. Contains no mutations."""

    advisory_text: str
    intent_confirmed: IntentClass
    governance_note: str | None
    trace_id: str


class CSOPolicyError(Exception):
    """Raised when a request violates the CSO advisory governance policy profile."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
