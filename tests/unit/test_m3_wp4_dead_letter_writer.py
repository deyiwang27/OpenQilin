from openqilin.communication_gateway.delivery.dlq_writer import (
    DeadLetterWriteRequest,
    InMemoryDeadLetterWriter,
)
from openqilin.data_access.repositories.communication import InMemoryCommunicationRepository
from openqilin.observability.audit.audit_writer import InMemoryAuditWriter
from openqilin.observability.metrics.recorder import InMemoryMetricRecorder


def test_dead_letter_writer_persists_record_and_emits_observability() -> None:
    repository = InMemoryCommunicationRepository()
    audit_writer = InMemoryAuditWriter()
    metric_recorder = InMemoryMetricRecorder()
    writer = InMemoryDeadLetterWriter(
        repository=repository,
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
    )

    record = writer.write_dead_letter(
        DeadLetterWriteRequest(
            task_id="task-dlq-001",
            trace_id="trace-dlq-001",
            principal_id="owner-dlq-001",
            idempotency_key="idem-dlq-001",
            message_id="msg-dlq-001",
            external_message_id="ext-dlq-001",
            connector="discord",
            command="msg_dispatch_retryable_nack",
            target="communication",
            route_key="discord_direct_message",
            endpoint="acp://discord/communication",
            error_code="communication_retry_exhausted",
            error_message="retry exhausted after 3 attempts",
            attempts=3,
            ledger_id="ledger-dlq-001",
        )
    )

    persisted = repository.get_dead_letter(record.dead_letter_id)
    assert persisted is not None
    assert persisted.error_code == "communication_retry_exhausted"
    assert persisted.attempts == 3
    assert persisted.connector == "discord"
    assert persisted.task_id == "task-dlq-001"

    dead_letters = writer.list_dead_letters()
    assert len(dead_letters) == 1
    assert dead_letters[0].dead_letter_id == record.dead_letter_id

    counter = metric_recorder.get_counter_value(
        "communication_dead_letter_total",
        labels={"connector": "discord", "reason_code": "communication_retry_exhausted"},
    )
    assert counter == 1

    events = audit_writer.get_events()
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "communication.dead_letter"
    assert event.outcome == "dead_lettered"
    assert event.trace_id == "trace-dlq-001"
    assert event.source == "communication_gateway_dlq"
    assert event.reason_code == "communication_retry_exhausted"
