from openqilin.budget_runtime.client import InMemoryBudgetRuntimeClient
from openqilin.budget_runtime.reservation_service import BudgetReservationService
from openqilin.budget_runtime.threshold_evaluator import estimate_cost_units
from openqilin.control_plane.identity.principal_resolver import resolve_principal
from openqilin.data_access.repositories.runtime_state import (
    InMemoryRuntimeStateRepository,
    TaskRecord,
)
from openqilin.task_orchestrator.admission.envelope_validator import validate_owner_command_envelope
from openqilin.testing.owner_command import build_owner_command_request_model


def _build_task(command: str) -> TaskRecord:
    payload = build_owner_command_request_model(
        action=command,
        args=["alpha"],
        actor_id="owner_budget_001",
        idempotency_key=f"idem-{command}-12345678",
        trace_id="trace-budget-test",
    )
    principal = resolve_principal(
        {
            "x-external-channel": "discord",
            "x-openqilin-actor-external-id": "owner_budget_001",
        }
    )
    envelope = validate_owner_command_envelope(payload=payload, principal=principal)
    repository = InMemoryRuntimeStateRepository()
    return repository.create_task_from_envelope(envelope)


def test_estimate_cost_units_is_positive() -> None:
    units = estimate_cost_units("run_task", ("arg1", "arg2"))
    assert units > 0


def test_budget_reservation_allows_and_is_replay_safe() -> None:
    task = _build_task("run_task")
    service = BudgetReservationService(client=InMemoryBudgetRuntimeClient())

    first = service.reserve_with_fail_closed(task)
    second = service.reserve_with_fail_closed(task)

    assert first.allowed is True
    assert second.allowed is True
    assert first.reservation is not None
    assert second.reservation is not None
    assert first.reservation.reservation_id == second.reservation.reservation_id


def test_budget_reservation_blocks_deny() -> None:
    task = _build_task("budget_deny_project")
    service = BudgetReservationService(client=InMemoryBudgetRuntimeClient())

    outcome = service.reserve_with_fail_closed(task)

    assert outcome.allowed is False
    assert outcome.error_code == "budget_denied"


def test_budget_reservation_blocks_uncertain_fail_closed() -> None:
    task = _build_task("budget_uncertain")
    service = BudgetReservationService(client=InMemoryBudgetRuntimeClient())

    outcome = service.reserve_with_fail_closed(task)

    assert outcome.allowed is False
    assert outcome.error_code == "budget_uncertain_fail_closed"


def test_budget_reservation_blocks_runtime_error_fail_closed() -> None:
    task = _build_task("budget_error")
    service = BudgetReservationService(client=InMemoryBudgetRuntimeClient())

    outcome = service.reserve_with_fail_closed(task)

    assert outcome.allowed is False
    assert outcome.error_code == "budget_runtime_error_fail_closed"
