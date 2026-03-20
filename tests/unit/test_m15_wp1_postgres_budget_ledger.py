from __future__ import annotations

from openqilin.budget_runtime.client import AlwaysAllowBudgetRuntimeClient
from openqilin.budget_runtime.models import (
    BudgetReservationInput,
    BudgetReservationResult,
    BudgetRuntimeClientProtocol,
)
from openqilin.budget_runtime.reservation_service import BudgetReservationService
from openqilin.control_plane.identity.principal_resolver import resolve_principal
from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.task_orchestrator.admission.envelope_validator import validate_owner_command_envelope
from openqilin.testing.owner_command import build_owner_command_request_model
from tests.testing.infra_stubs import InMemoryRuntimeStateRepository


class _HardBreachClient:
    def reserve(self, payload: BudgetReservationInput) -> BudgetReservationResult:
        return BudgetReservationResult(
            decision="hard_breach",
            reason_code="budget_quota_hard_breach",
            reason_message="limit exceeded",
            reservation_id=None,
            remaining_units=0,
            budget_version="test",
        )

    def settle(self, task_id: str, reservation_id: str, actual_units: int) -> None:
        return None

    def release(self, task_id: str, reservation_id: str) -> None:
        return None


class _CaptureClient:
    def __init__(self) -> None:
        self.last_payload: BudgetReservationInput | None = None

    def reserve(self, payload: BudgetReservationInput) -> BudgetReservationResult:
        self.last_payload = payload
        return BudgetReservationResult(
            decision="allow",
            reason_code="budget_reserved",
            reason_message="budget reserved",
            reservation_id="r1",
            remaining_units=42,
            budget_version="test",
        )

    def settle(self, task_id: str, reservation_id: str, actual_units: int) -> None:
        return None

    def release(self, task_id: str, reservation_id: str) -> None:
        return None


def _build_task(command: str, *, project_id: str | None) -> TaskRecord:
    payload = build_owner_command_request_model(
        action=command,
        args=["alpha"],
        actor_id="owner_budget_001",
        idempotency_key=f"idem-{command}-12345678",
        trace_id="trace-budget-test",
        project_id=project_id,
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


def test_budget_reservation_input_includes_project_id() -> None:
    payload = BudgetReservationInput(
        task_id="t1",
        request_id="r1",
        trace_id="trace-1",
        principal_id="owner_1",
        project_id="proj-123",
        command="run_task",
        args=("a",),
        estimated_cost_units=10,
    )

    assert payload.project_id == "proj-123"


def test_budget_decision_includes_hard_breach() -> None:
    reservation = BudgetReservationResult(
        decision="hard_breach",
        reason_code="budget_quota_hard_breach",
        reason_message="limit exceeded",
        reservation_id=None,
        remaining_units=0,
        budget_version="test",
    )

    assert reservation.decision == "hard_breach"


def test_always_allow_client_reserve_returns_allow() -> None:
    client = AlwaysAllowBudgetRuntimeClient()

    result = client.reserve(
        BudgetReservationInput(
            task_id="t1",
            request_id="r1",
            trace_id="trace-1",
            principal_id="owner_1",
            project_id="project-default",
            command="run_task",
            args=("a",),
            estimated_cost_units=10,
        )
    )

    assert result.decision == "allow"


def test_always_allow_client_settle_is_noop() -> None:
    client = AlwaysAllowBudgetRuntimeClient()

    client.settle("t1", "r1", 100)


def test_always_allow_client_release_is_noop() -> None:
    client = AlwaysAllowBudgetRuntimeClient()

    client.release("t1", "r1")


def test_always_allow_client_conforms_to_protocol() -> None:
    assert isinstance(AlwaysAllowBudgetRuntimeClient(), BudgetRuntimeClientProtocol)


def test_budget_reservation_service_maps_hard_breach_to_blocked() -> None:
    task = _build_task("run_task", project_id="proj-123")
    service = BudgetReservationService(client=_HardBreachClient())

    outcome = service.reserve_with_fail_closed(task)

    assert outcome.allowed is False
    assert outcome.error_code == "budget_quota_hard_breach"


def test_budget_reservation_service_uses_project_id_from_task() -> None:
    task = _build_task("run_task", project_id="proj-123")
    client = _CaptureClient()
    service = BudgetReservationService(client=client)

    service.reserve_with_fail_closed(task)

    assert client.last_payload is not None
    assert client.last_payload.project_id == "proj-123"


def test_budget_reservation_service_defaults_project_id_when_none() -> None:
    task = _build_task("run_task", project_id=None)
    client = _CaptureClient()
    service = BudgetReservationService(client=client)

    service.reserve_with_fail_closed(task)

    assert client.last_payload is not None
    assert client.last_payload.project_id == "project-default"
