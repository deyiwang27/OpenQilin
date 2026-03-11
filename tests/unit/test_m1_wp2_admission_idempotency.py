import pytest

from openqilin.control_plane.idempotency.ingress_dedupe import InMemoryIngressDedupe
from openqilin.control_plane.identity.principal_resolver import resolve_principal
from openqilin.control_plane.schemas.owner_commands import OwnerCommandRequest
from openqilin.data_access.repositories.runtime_state import InMemoryRuntimeStateRepository
from openqilin.task_orchestrator.admission.envelope_validator import (
    AdmissionEnvelope,
    validate_owner_command_envelope,
)
from openqilin.task_orchestrator.admission.idempotency import (
    AdmissionIdempotencyCoordinator,
    AdmissionIdempotencyError,
)


def _build_envelope(
    *,
    idempotency_key: str,
    args: list[str],
    trace_id: str,
) -> AdmissionEnvelope:
    payload = OwnerCommandRequest(
        command="run_task",
        args=args,
        idempotency_key=idempotency_key,
    )
    principal = resolve_principal(
        {
            "x-openqilin-user-id": "owner_123",
            "x-openqilin-connector": "discord",
        }
    )
    return validate_owner_command_envelope(payload=payload, principal=principal, trace_id=trace_id)


def test_admission_idempotency_returns_replay_without_new_task() -> None:
    coordinator = AdmissionIdempotencyCoordinator(
        dedupe_store=InMemoryIngressDedupe(),
        runtime_state_repo=InMemoryRuntimeStateRepository(),
    )
    envelope = _build_envelope(
        idempotency_key="idem-unit-replay-12345",
        args=["alpha"],
        trace_id="trace-1",
    )

    first = coordinator.resolve(envelope)
    second = coordinator.resolve(envelope)

    assert first.replayed is False
    assert second.replayed is True
    assert first.task.task_id == second.task.task_id
    assert first.task.request_id == second.task.request_id


def test_admission_idempotency_blocks_conflicting_payload_with_same_key() -> None:
    coordinator = AdmissionIdempotencyCoordinator(
        dedupe_store=InMemoryIngressDedupe(),
        runtime_state_repo=InMemoryRuntimeStateRepository(),
    )
    first_envelope = _build_envelope(
        idempotency_key="idem-unit-conflict-12345",
        args=["alpha"],
        trace_id="trace-1",
    )
    second_envelope = _build_envelope(
        idempotency_key="idem-unit-conflict-12345",
        args=["beta"],
        trace_id="trace-2",
    )

    _ = coordinator.resolve(first_envelope)
    with pytest.raises(AdmissionIdempotencyError) as exc:
        coordinator.resolve(second_envelope)

    assert exc.value.code == "idempotency_key_reused_with_different_payload"
