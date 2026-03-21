"""Budget runtime DTOs and protocol for governed reservation checks."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol, runtime_checkable


class BudgetConfigurationError(Exception):
    """Raised when the budget runtime client is not configured but is required."""


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
    model_class: str = "interactive_fast"


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

    def settle(
        self,
        task_id: str,
        actual_tokens: int,
        actual_cost_usd: Decimal,
        *,
        project_id: str = "",
        role: str = "",
        model_class: str = "",
    ) -> None:
        """
        Settle the reservation for task_id and record actual usage.

        Looks up the active reservation for task_id internally.
        Also inserts a budget_events row with actual usage data.
        No-op if no active reservation is found (idempotent).
        """
        ...

    def release(self, task_id: str) -> None:
        """
        Release the active reservation for task_id (task cancelled).

        No-op if no active reservation found.
        """
        ...
