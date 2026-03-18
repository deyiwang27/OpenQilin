"""CEO agent request/response models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CeoRequest:
    """Executive request routed to the CEO agent."""

    message: str
    intent: str
    context: dict[str, Any]
    proposal_id: str | None
    cso_review_outcome: str | None
    trace_id: str


@dataclass(frozen=True, slots=True)
class CeoResponse:
    """CEO response carrying a decision or routing directive."""

    decision: str | None
    advisory_text: str
    routing_hint: str | None
    trace_id: str


class CeoProposalGateError(PermissionError):
    """Raised when a proposal fails a mandatory CEO gate check."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "ceo_proposal_gate_denied"


class CeoCoApprovalError(PermissionError):
    """Raised when paired co-approval evidence is missing."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "ceo_coapproval_denied"
