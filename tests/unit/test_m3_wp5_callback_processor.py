from openqilin.control_plane.identity.principal_resolver import resolve_principal
from openqilin.data_access.repositories.runtime_state import InMemoryRuntimeStateRepository
from openqilin.observability.audit.audit_writer import InMemoryAuditWriter
from openqilin.observability.metrics.recorder import InMemoryMetricRecorder
from openqilin.task_orchestrator.admission.envelope_validator import validate_owner_command_envelope
from openqilin.task_orchestrator.callbacks.delivery_events import (
    DeliveryCallbackEvent,
    InMemoryDeliveryEventCallbackProcessor,
)
from openqilin.testing.owner_command import build_owner_command_request_model


def _build_runtime_state_repo_with_task() -> tuple[InMemoryRuntimeStateRepository, str]:
    payload = build_owner_command_request_model(
        action="msg_notify",
        args=["agent_cb"],
        actor_id="owner_cb_unit_001",
        idempotency_key="idem-callback-unit-12345",
        trace_id="trace-callback-unit-12345",
        target="communication",
    )
    principal = resolve_principal(
        {
            "x-external-channel": "discord",
            "x-openqilin-actor-external-id": "owner_cb_unit_001",
        }
    )
    envelope = validate_owner_command_envelope(payload=payload, principal=principal)
    repo = InMemoryRuntimeStateRepository()
    task = repo.create_task_from_envelope(envelope)
    repo.update_task_status(
        task.task_id,
        "dispatched",
        outcome_source="dispatch_communication",
        outcome_message="dispatch accepted",
        dispatch_target="communication",
        dispatch_id="acp-dispatch-001",
    )
    return repo, task.task_id


def test_callback_processor_applies_delivered_event_and_emits_observability() -> None:
    runtime_repo, task_id = _build_runtime_state_repo_with_task()
    audit_writer = InMemoryAuditWriter()
    metric_recorder = InMemoryMetricRecorder()
    processor = InMemoryDeliveryEventCallbackProcessor(
        runtime_state_repo=runtime_repo,
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
    )

    result = processor.process(
        DeliveryCallbackEvent(
            callback_id="cb-delivered-001",
            task_id=task_id,
            trace_id="trace-callback-unit-12345",
            dispatch_target="communication",
            delivery_outcome="delivered",
            message="delivery confirmed",
            dispatch_id="acp-dispatch-001",
        )
    )

    assert result.applied is True
    assert result.replayed is False
    assert result.task_status == "dispatched"
    task = runtime_repo.get_task_by_id(task_id)
    assert task is not None
    assert task.status == "dispatched"
    assert task.outcome_source == "callback_communication_delivery"
    assert task.outcome_message == "delivery confirmed"
    assert dict(task.outcome_details or ())["callback_id"] == "cb-delivered-001"
    assert (
        metric_recorder.get_counter_value(
            "communication_callback_events_total",
            labels={"outcome": "delivered", "replayed": "false"},
        )
        == 1
    )
    events = audit_writer.get_events()
    assert len(events) == 1
    assert events[0].event_type == "communication.callback.delivered"


def test_callback_processor_applies_dead_letter_event_and_blocks_task() -> None:
    runtime_repo, task_id = _build_runtime_state_repo_with_task()
    audit_writer = InMemoryAuditWriter()
    metric_recorder = InMemoryMetricRecorder()
    processor = InMemoryDeliveryEventCallbackProcessor(
        runtime_state_repo=runtime_repo,
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
    )

    result = processor.process(
        DeliveryCallbackEvent(
            callback_id="cb-dlq-001",
            task_id=task_id,
            trace_id="trace-callback-unit-12345",
            dispatch_target="communication",
            delivery_outcome="dead_lettered",
            message="dead-letter routed",
            reason_code="communication_retry_exhausted",
            dead_letter_id="dlq-001",
        )
    )

    assert result.applied is True
    assert result.replayed is False
    assert result.task_status == "blocked"
    task = runtime_repo.get_task_by_id(task_id)
    assert task is not None
    assert task.status == "blocked"
    assert task.outcome_source == "callback_communication_dead_letter"
    assert task.outcome_error_code == "communication_retry_exhausted"
    details = dict(task.outcome_details or ())
    assert details["dead_letter_id"] == "dlq-001"
    assert (
        metric_recorder.get_counter_value(
            "communication_callback_events_total",
            labels={"outcome": "dead_lettered", "replayed": "false"},
        )
        == 1
    )
    events = audit_writer.get_events()
    assert len(events) == 1
    assert events[0].event_type == "communication.callback.dead_lettered"


def test_callback_processor_is_duplicate_safe_for_replayed_callback_id() -> None:
    runtime_repo, task_id = _build_runtime_state_repo_with_task()
    audit_writer = InMemoryAuditWriter()
    metric_recorder = InMemoryMetricRecorder()
    processor = InMemoryDeliveryEventCallbackProcessor(
        runtime_state_repo=runtime_repo,
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
    )
    event = DeliveryCallbackEvent(
        callback_id="cb-replay-001",
        task_id=task_id,
        trace_id="trace-callback-unit-12345",
        dispatch_target="communication",
        delivery_outcome="delivered",
        message="delivery confirmed",
    )

    first = processor.process(event)
    second = processor.process(event)

    assert first.applied is True
    assert first.replayed is False
    assert second.applied is False
    assert second.replayed is True
    assert (
        metric_recorder.get_counter_value(
            "communication_callback_events_total",
            labels={"outcome": "delivered", "replayed": "false"},
        )
        == 1
    )
    assert (
        metric_recorder.get_counter_value(
            "communication_callback_events_total",
            labels={"outcome": "delivered", "replayed": "true"},
        )
        == 1
    )
    events = audit_writer.get_events()
    assert len(events) == 1
