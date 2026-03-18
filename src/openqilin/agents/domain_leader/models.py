"""Domain Leader agent request/response models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DomainLeaderRequest:
    """Escalation or clarification request routed to the Domain Leader.

    Requires ``project_id`` — DL is always scoped to a project context.
    Rejected without it (``DomainLeaderProjectContextError``).
    """

    project_id: str
    message: str
    requesting_agent: str
    trace_id: str
    task_id: str | None = None


@dataclass(frozen=True, slots=True)
class DomainLeaderResponse:
    """Domain response produced by the Domain Leader.

    Never sent directly to the Discord channel — PM synthesises the channel reply.

    ``domain_outcome``:
      - ``"resolved"``             — DL resolved the escalation; no further escalation needed.
      - ``"needs_rework"``         — specialist output requires rework; see ``rework_recommendations``.
      - ``"domain_risk_escalation"`` — material domain risk that DL cannot resolve; escalate to PM.

    ``escalate_to`` is ``"project_manager"`` on ``domain_risk_escalation``; ``None`` otherwise.
    """

    advisory_text: str
    domain_outcome: str
    trace_id: str
    escalate_to: str | None = None
    rework_recommendations: str | None = None


@dataclass(frozen=True, slots=True)
class SpecialistReviewRequest:
    """Request for DL to review a specialist's output."""

    task_id: str
    project_id: str
    specialist_output: str
    trace_id: str


@dataclass(frozen=True, slots=True)
class SpecialistReviewOutcome:
    """Outcome of DL specialist output review.

    ``outcome``: ``"allow"`` (quality OK) or ``"needs_rework"`` (quality insufficient).
    """

    outcome: str
    trace_id: str
    rework_recommendations: str | None = None


class DomainLeaderProjectContextError(ValueError):
    """Raised when DL receives a request without a ``project_id``."""

    def __init__(self) -> None:
        super().__init__("DomainLeader requires project_id — rejected without project context")
        self.code = "dl_project_context_required"


class DomainLeaderCommandDeniedError(PermissionError):
    """Raised when code attempts to issue a direct command to a specialist via DL.

    DL has ``command: deny`` authority — all specialist interactions must route through PM.
    """

    def __init__(self, specialist_id: str) -> None:
        super().__init__(
            f"DomainLeader cannot issue commands directly to specialist '{specialist_id}'. "
            "All specialist interactions must route through ProjectManager."
        )
        self.code = "dl_command_denied"
        self.specialist_id = specialist_id
