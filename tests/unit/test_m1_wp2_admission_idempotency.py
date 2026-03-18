import pytest

from openqilin.control_plane.idempotency.ingress_dedupe import InMemoryIngressDedupe
from openqilin.control_plane.identity.principal_resolver import resolve_principal
from tests.testing.infra_stubs import InMemoryRuntimeStateRepository
from openqilin.task_orchestrator.admission.envelope_validator import (
    AdmissionEnvelope,
    validate_owner_command_envelope,
)
from openqilin.task_orchestrator.admission.idempotency import (
    AdmissionIdempotencyCoordinator,
    AdmissionIdempotencyError,
)
from openqilin.testing.owner_command import build_owner_command_request_model


def _build_envelope(
    *,
    idempotency_key: str,
    args: list[str],
    trace_id: str,
    content_tag: str = "default",
) -> AdmissionEnvelope:
    payload = build_owner_command_request_model(
        action="run_task",
        args=args,
        actor_id="owner_123",
        idempotency_key=idempotency_key,
        trace_id=trace_id,
        content=f"content-{content_tag}",
    )
    principal = resolve_principal(
        {
            "x-external-channel": "discord",
            "x-openqilin-actor-external-id": "owner_123",
        }
    )
    return validate_owner_command_envelope(payload=payload, principal=principal)


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


def test_admission_idempotency_blocks_conflicting_metadata_with_same_key() -> None:
    coordinator = AdmissionIdempotencyCoordinator(
        dedupe_store=InMemoryIngressDedupe(),
        runtime_state_repo=InMemoryRuntimeStateRepository(),
    )
    first_envelope = _build_envelope(
        idempotency_key="idem-unit-metadata-conflict-12345",
        args=["alpha"],
        trace_id="trace-1",
        content_tag="discord",
    )
    second_envelope = _build_envelope(
        idempotency_key="idem-unit-metadata-conflict-12345",
        args=["alpha"],
        trace_id="trace-2",
        content_tag="telegram",
    )

    _ = coordinator.resolve(first_envelope)
    with pytest.raises(AdmissionIdempotencyError) as exc:
        coordinator.resolve(second_envelope)

    assert exc.value.code == "idempotency_key_reused_with_different_payload"
