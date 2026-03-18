from openqilin.communication_gateway.callbacks.outcome_notifier import (
    CommunicationOutcomeNotification,
    CommunicationOutcomeNotifier,
)
from openqilin.control_plane.identity.principal_resolver import resolve_principal
from tests.testing.infra_stubs import InMemoryRuntimeStateRepository
from openqilin.observability.testing.stubs import InMemoryAuditWriter
from openqilin.observability.testing.stubs import InMemoryMetricRecorder
from openqilin.task_orchestrator.admission.envelope_validator import validate_owner_command_envelope
from openqilin.task_orchestrator.callbacks.delivery_events import (
    InMemoryDeliveryEventCallbackProcessor,
)
from openqilin.testing.owner_command import build_owner_command_request_model


def _build_notifier_and_task() -> tuple[CommunicationOutcomeNotifier, str]:
    payload = build_owner_command_request_model(
        action="msg_notify",
        args=["agent_contract"],
        actor_id="owner_callback_contract",
        idempotency_key="idem-callback-contract-12345",
        trace_id="trace-callback-contract-12345",
        target="communication",
    )
    principal = resolve_principal(
        {
            "x-external-channel": "discord",
            "x-openqilin-actor-external-id": "owner_callback_contract",
        }
    )
    envelope = validate_owner_command_envelope(payload=payload, principal=principal)
    runtime_state_repo = InMemoryRuntimeStateRepository()
    task = runtime_state_repo.create_task_from_envelope(envelope)
    runtime_state_repo.update_task_status(task.task_id, "authorized")
    runtime_state_repo.update_task_status(
        task.task_id,
        "dispatched",
        dispatch_target="communication",
        dispatch_id="acp-contract-callback-001",
        outcome_source="dispatch_communication",
        outcome_message="dispatch accepted",
    )
    processor = InMemoryDeliveryEventCallbackProcessor(
        runtime_state_repo=runtime_state_repo,
        audit_writer=InMemoryAuditWriter(),
        metric_recorder=InMemoryMetricRecorder(),
    )
    return CommunicationOutcomeNotifier(callback_processor=processor), task.task_id


def test_callback_notifier_result_contract_for_delivered_event() -> None:
    notifier, task_id = _build_notifier_and_task()

    result = notifier.notify_delivery_outcome(
        CommunicationOutcomeNotification(
            callback_id="cb-contract-001",
            task_id=task_id,
            trace_id="trace-callback-contract-12345",
            dispatch_target="communication",
            delivery_outcome="delivered",
            message="delivery confirmed",
            dispatch_id="acp-contract-callback-001",
        )
    )

    payload = {
        "applied": result.applied,
        "replayed": result.replayed,
        "task_status": result.task_status,
        "message": result.message,
        "reason_code": result.reason_code,
    }
    assert set(payload.keys()) == {
        "applied",
        "replayed",
        "task_status",
        "message",
        "reason_code",
    }
    assert payload["applied"] is True
    assert payload["replayed"] is False
    assert payload["task_status"] == "dispatched"


def test_callback_notifier_result_contract_for_dead_letter_event() -> None:
    notifier, task_id = _build_notifier_and_task()

    result = notifier.notify_delivery_outcome(
        CommunicationOutcomeNotification(
            callback_id="cb-contract-dlq-001",
            task_id=task_id,
            trace_id="trace-callback-contract-12345",
            dispatch_target="communication",
            delivery_outcome="dead_lettered",
            message="dead-letter confirmed",
            reason_code="communication_retry_exhausted",
            dead_letter_id="dlq-contract-001",
        )
    )

    payload = {
        "applied": result.applied,
        "replayed": result.replayed,
        "task_status": result.task_status,
        "message": result.message,
        "reason_code": result.reason_code,
    }
    assert set(payload.keys()) == {
        "applied",
        "replayed",
        "task_status",
        "message",
        "reason_code",
    }
    assert payload["applied"] is True
    assert payload["replayed"] is False
    assert payload["task_status"] == "blocked"
    assert payload["reason_code"] == "communication_retry_exhausted"
