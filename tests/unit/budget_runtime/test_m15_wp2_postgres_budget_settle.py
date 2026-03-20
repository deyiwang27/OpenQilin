from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Literal
from unittest.mock import Mock

from openqilin.budget_runtime.client import PostgresBudgetRuntimeClient
from openqilin.budget_runtime.cost_evaluator import CostEstimate
from openqilin.budget_runtime.models import BudgetReservationInput


@dataclass
class _FakeResult:
    row: object | None

    def fetchone(self) -> object | None:
        return self.row


class _FakeSession:
    def __init__(self, *, allocation_row: object, spent_row: object) -> None:
        self._allocation_row = allocation_row
        self._spent_row = spent_row
        self.committed = False

    def execute(self, statement: Any, parameters: dict[str, object]) -> _FakeResult:
        _ = parameters
        sql = str(statement)
        if "FROM budget_allocations" in sql:
            return _FakeResult(self._allocation_row)
        if "FROM budget_reservations" in sql:
            return _FakeResult(self._spent_row)
        raise AssertionError(f"unexpected SQL: {sql}")

    def commit(self) -> None:
        self.committed = True


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def __enter__(self) -> _FakeSession:
        return self._session

    def __exit__(self, exc_type: object, exc: object, tb: object) -> Literal[False]:
        _ = (exc_type, exc, tb)
        return False


class _FakeSessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def __call__(self) -> _FakeSessionContext:
        return _FakeSessionContext(self._session)


def _build_payload(*, estimated_cost_units: int = 10) -> BudgetReservationInput:
    return BudgetReservationInput(
        task_id="task-1",
        request_id="req-1",
        trace_id="trace-1",
        principal_id="owner-1",
        project_id="project-default",
        command="llm_reason",
        args=("arg1",),
        estimated_cost_units=estimated_cost_units,
        model_class="interactive_fast",
    )


def test_settle_calls_settle_reservation_and_insert_event() -> None:
    ledger_repo = Mock()
    ledger_repo.DEFAULT_PROJECT_ID = "project-default"
    ledger_repo.find_active_reservation_id.return_value = "resv-123"
    client = PostgresBudgetRuntimeClient(ledger_repo=ledger_repo, cost_evaluator=Mock())

    client.settle(
        "task-1",
        321,
        Decimal("0.42"),
        project_id="project-123",
        role="owner",
        model_class="interactive_fast",
    )

    ledger_repo.settle_reservation.assert_called_once_with(reservation_id="resv-123")
    ledger_repo.insert_event.assert_called_once_with(
        task_id="task-1",
        project_id="project-123",
        role="owner",
        model_class="interactive_fast",
        actual_tokens=321,
        actual_cost_usd=Decimal("0.42"),
    )


def test_settle_noop_when_no_active_reservation() -> None:
    ledger_repo = Mock()
    ledger_repo.DEFAULT_PROJECT_ID = "project-default"
    ledger_repo.find_active_reservation_id.return_value = None
    client = PostgresBudgetRuntimeClient(ledger_repo=ledger_repo, cost_evaluator=Mock())

    client.settle("task-1", 10, Decimal("0.01"))

    ledger_repo.settle_reservation.assert_not_called()
    ledger_repo.insert_event.assert_not_called()


def test_settle_does_not_raise_on_db_error() -> None:
    ledger_repo = Mock()
    ledger_repo.DEFAULT_PROJECT_ID = "project-default"
    ledger_repo.find_active_reservation_id.return_value = "resv-123"
    ledger_repo.settle_reservation.side_effect = Exception("db down")
    client = PostgresBudgetRuntimeClient(ledger_repo=ledger_repo, cost_evaluator=Mock())

    client.settle("task-1", 10, Decimal("0.01"))


def test_release_calls_release_reservation() -> None:
    ledger_repo = Mock()
    ledger_repo.find_active_reservation_id.return_value = "resv-123"
    client = PostgresBudgetRuntimeClient(ledger_repo=ledger_repo, cost_evaluator=Mock())

    client.release("task-1")

    ledger_repo.release_reservation.assert_called_once_with(reservation_id="resv-123")


def test_release_noop_when_no_active_reservation() -> None:
    ledger_repo = Mock()
    ledger_repo.find_active_reservation_id.return_value = None
    client = PostgresBudgetRuntimeClient(ledger_repo=ledger_repo, cost_evaluator=Mock())

    client.release("task-1")

    ledger_repo.release_reservation.assert_not_called()


def test_reserve_uses_token_cost_evaluator_not_fixed_multiplier() -> None:
    allocation_row = SimpleNamespace(
        currency_limit_usd=Decimal("100.0"),
        quota_limit_tokens=20_000,
    )
    spent_row = SimpleNamespace(
        spent_tokens=0,
        spent_usd=Decimal("0"),
    )
    fake_session = _FakeSession(allocation_row=allocation_row, spent_row=spent_row)

    ledger_repo = Mock()
    ledger_repo.DEFAULT_PROJECT_ID = "project-default"
    ledger_repo.session_factory = _FakeSessionFactory(fake_session)
    ledger_repo.insert_reservation.return_value = SimpleNamespace(id="resv-1")

    evaluator = Mock()
    evaluator.estimate.return_value = CostEstimate(
        usd_estimate=Decimal("1.0"),
        quota_tokens_estimate=9999,
    )

    client = PostgresBudgetRuntimeClient(ledger_repo=ledger_repo, cost_evaluator=evaluator)
    result = client.reserve(_build_payload(estimated_cost_units=123))

    assert result.decision == "allow"
    evaluator.estimate.assert_called_once_with("interactive_fast", 123)
    ledger_repo.insert_reservation.assert_called_once()
    call_kwargs = ledger_repo.insert_reservation.call_args.kwargs
    assert call_kwargs["reserved_usd"] == Decimal("1.0")
    assert call_kwargs["reserved_tokens"] == 9999


def test_free_tier_reserve_quota_breach_returns_hard_breach() -> None:
    allocation_row = SimpleNamespace(
        currency_limit_usd=Decimal("100.0"),
        quota_limit_tokens=1,
    )
    spent_row = SimpleNamespace(
        spent_tokens=0,
        spent_usd=Decimal("0"),
    )
    fake_session = _FakeSession(allocation_row=allocation_row, spent_row=spent_row)

    ledger_repo = Mock()
    ledger_repo.DEFAULT_PROJECT_ID = "project-default"
    ledger_repo.session_factory = _FakeSessionFactory(fake_session)

    evaluator = Mock()
    evaluator.estimate.return_value = CostEstimate(
        usd_estimate=Decimal("0.0"),
        quota_tokens_estimate=500,
    )

    client = PostgresBudgetRuntimeClient(ledger_repo=ledger_repo, cost_evaluator=evaluator)
    result = client.reserve(_build_payload())

    assert result.decision == "hard_breach"
    assert result.reason_code == "budget_quota_hard_breach"
    ledger_repo.insert_reservation.assert_not_called()
