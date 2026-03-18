"""Budget runtime client shell."""

from __future__ import annotations

from uuid import uuid4

from openqilin.budget_runtime.models import BudgetReservationInput, BudgetReservationResult


class BudgetRuntimeClientError(RuntimeError):
    """Raised when budget runtime call cannot be completed."""


class AlwaysAllowBudgetRuntimeClient:
    """Always-allow budget client used until real budget service is wired (M14)."""

    def __init__(self, budget_version: str = "m1-budget-shell-v1") -> None:
        self._budget_version = budget_version
        self._remaining_units = 10_000

    def reserve(self, payload: BudgetReservationInput) -> BudgetReservationResult:
        """Evaluate and reserve budget for an admitted task."""

        if payload.command == "budget_error":
            raise BudgetRuntimeClientError("simulated budget runtime failure")

        if payload.command == "budget_uncertain":
            return BudgetReservationResult(
                decision="uncertain",
                reason_code="budget_uncertain",
                reason_message="budget runtime returned uncertainty",
                reservation_id=None,
                remaining_units=None,
                budget_version=self._budget_version,
            )

        if payload.command.startswith("budget_deny_"):
            return BudgetReservationResult(
                decision="deny",
                reason_code="budget_denied",
                reason_message="budget threshold denied request",
                reservation_id=None,
                remaining_units=self._remaining_units,
                budget_version=self._budget_version,
            )

        if payload.estimated_cost_units > self._remaining_units:
            return BudgetReservationResult(
                decision="deny",
                reason_code="budget_insufficient_capacity",
                reason_message="insufficient remaining budget units",
                reservation_id=None,
                remaining_units=self._remaining_units,
                budget_version=self._budget_version,
            )

        self._remaining_units -= payload.estimated_cost_units
        return BudgetReservationResult(
            decision="allow",
            reason_code="budget_reserved",
            reason_message="budget reserved",
            reservation_id=str(uuid4()),
            remaining_units=self._remaining_units,
            budget_version=self._budget_version,
        )


# Backward-compat alias
InMemoryBudgetRuntimeClient = AlwaysAllowBudgetRuntimeClient
