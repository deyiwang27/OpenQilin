"""Budget runtime DTOs and protocol for governed reservation checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

DEFAULT_BUDGET_PROJECT_ID: str = "project-default"

BudgetDecision = Literal["allow", "deny", "uncertain", "hard_breach"]


@dataclass(frozen=True, slots=True)
class BudgetReservationInput:
    """Normalized budget reservation request."""

    task_id: str
    request_id: str
    trace_id: str
    principal_id: str
    project_id: str
    command: str
    args: tuple[str, ...]
    estimated_cost_units: int


@dataclass(frozen=True, slots=True)
class BudgetReservationResult:
    """Budget reservation decision output."""

    decision: BudgetDecision
    reason_code: str
    reason_message: str
    reservation_id: str | None
    remaining_units: int | None
    budget_version: str


@runtime_checkable
class BudgetRuntimeClientProtocol(Protocol):
    """Structural protocol for runtime budget reservation clients."""

    def reserve(self, payload: BudgetReservationInput) -> BudgetReservationResult:
        """Evaluate and reserve budget for an admitted task."""
        ...

    def settle(self, task_id: str, reservation_id: str, actual_units: int) -> None:
        """Settle a prior reservation when task execution completes."""
        ...

    def release(self, task_id: str, reservation_id: str) -> None:
        """Release a prior reservation when task execution is cancelled."""
        ...
