"""Budget reservation service with fail-closed behavior."""

from __future__ import annotations

from dataclasses import dataclass

from openqilin.budget_runtime.client import InMemoryBudgetRuntimeClient
from openqilin.budget_runtime.models import BudgetReservationInput, BudgetReservationResult
from openqilin.budget_runtime.threshold_evaluator import estimate_cost_units
from openqilin.data_access.repositories.runtime_state import TaskRecord


@dataclass(frozen=True, slots=True)
class BudgetFailClosedOutcome:
    """Budget decision result used by ingress router."""

    allowed: bool
    error_code: str | None
    message: str
    reservation: BudgetReservationResult | None


class BudgetReservationService:
    """Applies budget checks and fail-closed semantics for admitted tasks."""

    def __init__(self, client: InMemoryBudgetRuntimeClient) -> None:
        self._client = client
        self._task_outcomes: dict[str, BudgetFailClosedOutcome] = {}

    def reserve_with_fail_closed(self, task: TaskRecord) -> BudgetFailClosedOutcome:
        """Reserve budget for task, replay-safe by task id."""

        existing = self._task_outcomes.get(task.task_id)
        if existing is not None:
            return existing

        payload = BudgetReservationInput(
            task_id=task.task_id,
            request_id=task.request_id,
            trace_id=task.trace_id,
            principal_id=task.principal_id,
            command=task.command,
            args=task.args,
            estimated_cost_units=estimate_cost_units(task.command, task.args),
        )

        try:
            reservation = self._client.reserve(payload)
        except Exception as error:
            outcome = BudgetFailClosedOutcome(
                allowed=False,
                error_code="budget_runtime_error_fail_closed",
                message=f"budget reservation failed: {error}",
                reservation=None,
            )
            self._task_outcomes[task.task_id] = outcome
            return outcome

        if reservation.decision == "allow":
            outcome = BudgetFailClosedOutcome(
                allowed=True,
                error_code=None,
                message=reservation.reason_message,
                reservation=reservation,
            )
            self._task_outcomes[task.task_id] = outcome
            return outcome

        if reservation.decision == "deny":
            outcome = BudgetFailClosedOutcome(
                allowed=False,
                error_code=reservation.reason_code,
                message=reservation.reason_message,
                reservation=reservation,
            )
            self._task_outcomes[task.task_id] = outcome
            return outcome

        outcome = BudgetFailClosedOutcome(
            allowed=False,
            error_code="budget_uncertain_fail_closed",
            message="budget decision uncertain; fail-closed block applied",
            reservation=reservation,
        )
        self._task_outcomes[task.task_id] = outcome
        return outcome
