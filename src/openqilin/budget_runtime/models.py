"""Budget runtime DTOs for governed reservation checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BudgetDecision = Literal["allow", "deny", "uncertain"]


@dataclass(frozen=True, slots=True)
class BudgetReservationInput:
    """Normalized budget reservation request."""

    task_id: str
    request_id: str
    trace_id: str
    principal_id: str
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
