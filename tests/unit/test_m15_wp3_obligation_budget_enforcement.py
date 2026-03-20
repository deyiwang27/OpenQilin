"""M15-WP3: budget enforcement must be conditioned on reserve_budget obligation."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock

from openqilin.budget_runtime.models import BudgetReservationResult
from openqilin.budget_runtime.reservation_service import BudgetFailClosedOutcome
from openqilin.policy_runtime_integration.obligations import (
    ObligationContext,
    ObligationDispatcher,
)
from openqilin.task_orchestrator.state.state_machine import route_after_obligation
from openqilin.task_orchestrator.workflow.state_models import TaskState


def _make_context(**overrides: object) -> ObligationContext:
    audit_writer = MagicMock()
    runtime_state_repo = MagicMock()
    budget_service = MagicMock()
    budget_service.reserve_with_fail_closed.return_value = BudgetFailClosedOutcome(
        allowed=True,
        error_code=None,
        message="budget reservation approved",
        reservation=BudgetReservationResult(
            decision="allow",
            reason_code="budget_allow",
            reason_message="budget reservation approved",
            reservation_id="res-001",
            remaining_units=1000,
            budget_version="budget-v1",
        ),
    )
    task_record = MagicMock()

    context: dict[str, object] = {
        "trace_id": "trace-001",
        "task_id": "task-001",
        "request_id": "req-001",
        "principal_id": "owner_001",
        "principal_role": "owner",
        "action": "msg_notify",
        "target": "ceo",
        "project_id": "project-default",
        "policy_version": "policy-v2",
        "policy_hash": "policy-hash-abc",
        "rule_ids": ("POL-001",),
        "audit_writer": audit_writer,
        "runtime_state_repo": runtime_state_repo,
        "budget_reservation_service": budget_service,
        "task_record": task_record,
    }
    context.update(overrides)
    return ObligationContext(**context)  # type: ignore[arg-type]


def test_route_after_obligation_satisfied_routes_to_dispatch_node() -> None:
    state = cast(TaskState, {"obligation_satisfied": True, "final_state": "authorized"})
    assert route_after_obligation(state) == "dispatch_node"


def test_route_after_obligation_unsatisfied_routes_to_end() -> None:
    state = cast(TaskState, {"obligation_satisfied": False, "final_state": "blocked"})
    assert route_after_obligation(state) == "__end__"


def test_plain_allow_budget_not_reserved() -> None:
    context = _make_context()
    result = ObligationDispatcher().apply((), context)

    assert result.all_satisfied
    context.budget_reservation_service.reserve_with_fail_closed.assert_not_called()  # type: ignore[attr-defined]


def test_allow_without_reserve_budget_obligation_budget_not_reserved() -> None:
    context = _make_context()
    result = ObligationDispatcher().apply(("emit_audit_event",), context)

    assert result.all_satisfied
    context.budget_reservation_service.reserve_with_fail_closed.assert_not_called()  # type: ignore[attr-defined]


def test_reserve_budget_obligation_calls_reservation_service() -> None:
    context = _make_context()
    result = ObligationDispatcher().apply(("reserve_budget",), context)

    assert result.all_satisfied
    context.budget_reservation_service.reserve_with_fail_closed.assert_called_once()  # type: ignore[attr-defined]


def test_reserve_budget_uncertain_blocks_obligation_chain() -> None:
    context = _make_context()
    budget_service = cast(MagicMock, context.budget_reservation_service)
    budget_service.reserve_with_fail_closed.return_value = BudgetFailClosedOutcome(
        allowed=False,
        error_code="budget_uncertain_fail_closed",
        message="budget decision uncertain; fail-closed block applied",
        reservation=BudgetReservationResult(
            decision="uncertain",
            reason_code="uncertain",
            reason_message="uncertain budget decision",
            reservation_id=None,
            remaining_units=None,
            budget_version="budget-v1",
        ),
    )

    result = ObligationDispatcher().apply(("emit_audit_event", "reserve_budget"), context)

    assert not result.all_satisfied
    assert result.blocking_obligation == "reserve_budget"


def test_reserve_budget_hard_breach_blocks() -> None:
    context = _make_context()
    budget_service = cast(MagicMock, context.budget_reservation_service)
    budget_service.reserve_with_fail_closed.return_value = BudgetFailClosedOutcome(
        allowed=False,
        error_code="budget_quota_hard_breach",
        message="quota hard breach",
        reservation=BudgetReservationResult(
            decision="hard_breach",
            reason_code="budget_hard_breach",
            reason_message="quota hard breach",
            reservation_id=None,
            remaining_units=None,
            budget_version="budget-v1",
        ),
    )

    result = ObligationDispatcher().apply(("reserve_budget",), context)

    assert not result.all_satisfied
    assert result.blocking_obligation == "reserve_budget"
