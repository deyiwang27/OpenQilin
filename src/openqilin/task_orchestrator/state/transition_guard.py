"""Task state transition guard for H-2: invalid state transition prevention.

All calls to update_task_status must pass through assert_legal_transition
before writing to the repository.  Any attempt to move a task to a status
that is not reachable from its current status raises InvalidStateTransitionError.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

# Legal forward transitions for the task lifecycle.
# Terminal states (completed, failed, cancelled) have no outbound edges.
LEGAL_TRANSITIONS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "queued": frozenset({"authorized", "blocked", "cancelled", "failed"}),
        "authorized": frozenset({"dispatched", "blocked", "failed", "cancelled"}),
        "dispatched": frozenset({"running", "blocked", "completed", "failed", "cancelled"}),
        "running": frozenset({"completed", "failed", "blocked", "cancelled"}),
        "blocked": frozenset({"queued", "dispatched", "cancelled", "failed"}),
        "completed": frozenset(),
        "failed": frozenset(),
        "cancelled": frozenset(),
    }
)


class InvalidStateTransitionError(ValueError):
    """Raised when a state transition is not in the legal transition graph."""

    def __init__(self, current: str, next_state: str) -> None:
        super().__init__(f"illegal task state transition: {current!r} → {next_state!r}")
        self.current = current
        self.next_state = next_state


def assert_legal_transition(current: str, next_state: str) -> None:
    """Raise InvalidStateTransitionError if current → next_state is not a legal transition.

    Unknown states (not in LEGAL_TRANSITIONS) are treated as having no legal
    successors and always raise.
    """

    allowed = LEGAL_TRANSITIONS.get(current, frozenset())
    if next_state not in allowed:
        raise InvalidStateTransitionError(current=current, next_state=next_state)
