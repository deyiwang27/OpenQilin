"""CSO agent request/response models."""

from __future__ import annotations

from dataclasses import dataclass

from openqilin.control_plane.grammar.models import ChatContext, IntentClass


@dataclass(frozen=True, slots=True)
class CSORequest:
    """Portfolio strategy advisory request routed to the CSO agent."""

    message: str
    intent: IntentClass
    context: ChatContext
    trace_id: str
    proposal_id: str | None = None
    portfolio_context: str | None = None


@dataclass(frozen=True, slots=True)
class CSOConflictFlag:
    """Structured strategic conflict advisory outcome.

    Not an exception — CSO advisory is informational. Callers decide whether to
    gate on the conflict or surface it as context for the next governance actor.

    ``flag_type`` values: ``"strategic_conflict"`` | ``"needs_revision"``
    ``escalate_to``: ``"ceo"`` for strategic conflicts; ``None`` for revision flags.
    """

    flag_type: str
    reason: str
    escalate_to: str | None = None


@dataclass(frozen=True, slots=True)
class CSOResponse:
    """Portfolio strategy advisory response from the CSO agent. Contains no mutations."""

    advisory_text: str
    intent_confirmed: IntentClass
    trace_id: str
    strategic_note: str | None = None
    conflict_flag: CSOConflictFlag | None = None
