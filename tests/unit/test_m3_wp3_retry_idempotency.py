from openqilin.communication_gateway.delivery.publisher import (
    InMemoryDeliveryPublisher,
    PublishRequest,
)
from openqilin.communication_gateway.delivery.retry_scheduler import DeterministicRetryScheduler


def _publish_request(
    *,
    command: str,
    idempotency_key: str = "idem-wp3-001",
    message_id: str = "msg-wp3-001",
    external_message_id: str = "ext-wp3-001",
) -> PublishRequest:
    return PublishRequest(
        task_id="task-wp3-001",
        trace_id="trace-wp3-001",
        principal_id="owner-wp3-001",
        idempotency_key=idempotency_key,
        message_id=message_id,
        external_message_id=external_message_id,
        connector="discord",
        command=command,
        target="communication",
        args=("agent_1",),
        project_id="project_1",
        route_key="discord_direct_message",
        endpoint="acp://discord/communication",
    )


def test_retry_scheduler_backoff_policy_is_deterministic() -> None:
    scheduler = DeterministicRetryScheduler(max_attempts=3, base_backoff_seconds=2)

    first = scheduler.schedule_next(
        attempt=1,
        error_code="acp_delivery_nack_retryable",
        retryable=True,
    )
    second = scheduler.schedule_next(
        attempt=2,
        error_code="acp_delivery_nack_retryable",
        retryable=True,
    )
    exhausted = scheduler.schedule_next(
        attempt=3,
        error_code="acp_delivery_nack_retryable",
        retryable=True,
    )
    blocked = scheduler.schedule_next(
        attempt=1,
        error_code="acp_contract_rejected",
        retryable=False,
    )

    assert first.retry is True
    assert first.next_attempt == 2
    assert first.backoff_seconds == 2
    assert second.retry is True
    assert second.next_attempt == 3
    assert second.backoff_seconds == 4
    assert exhausted.retry is False
    assert exhausted.reason_code == "communication_retry_exhausted"
    assert blocked.retry is False
    assert blocked.reason_code == "communication_retry_not_allowed"


def test_publisher_retries_retryable_nack_then_accepts() -> None:
    publisher = InMemoryDeliveryPublisher()

    receipt = publisher.publish(_publish_request(command="msg_dispatch_retry_then_ack"))

    assert receipt.accepted is True
    assert receipt.dispatch_id
    records = publisher.list_message_records(task_id="task-wp3-001")
    assert len(records) == 2
    assert records[0].attempt == 1
    assert records[0].state == "nacked"
    assert records[0].retryable is True
    assert records[1].attempt == 2
    assert records[1].state == "acked"
    idempotency_records = publisher.list_idempotency_records()
    assert len(idempotency_records) == 1
    assert idempotency_records[0].status == "completed"
    assert idempotency_records[0].attempt_count == 2


def test_publisher_suppresses_duplicate_delivery_without_resending() -> None:
    publisher = InMemoryDeliveryPublisher()
    request = _publish_request(command="msg_notify")

    first = publisher.publish(request)
    second = publisher.publish(request)

    assert first.accepted is True
    assert second.accepted is True
    assert second.dispatch_id == first.dispatch_id
    assert second.ledger_id == first.ledger_id
    records = publisher.list_message_records(task_id="task-wp3-001")
    assert len(records) == 1
    idempotency_records = publisher.list_idempotency_records()
    assert len(idempotency_records) == 1
    assert idempotency_records[0].attempt_count == 1


def test_publisher_returns_retry_exhausted_after_max_attempts() -> None:
    publisher = InMemoryDeliveryPublisher()

    receipt = publisher.publish(_publish_request(command="msg_dispatch_retryable_nack"))

    assert receipt.accepted is False
    assert receipt.error_code == "communication_retry_exhausted"
    assert receipt.retryable is False
    records = publisher.list_message_records(task_id="task-wp3-001")
    assert len(records) == 3
    assert [record.attempt for record in records] == [1, 2, 3]
    assert all(record.state == "nacked" for record in records)
    idempotency_records = publisher.list_idempotency_records()
    assert len(idempotency_records) == 1
    assert idempotency_records[0].attempt_count == 3


def test_publisher_rejects_idempotency_conflict_for_changed_payload() -> None:
    publisher = InMemoryDeliveryPublisher()
    first = _publish_request(command="msg_notify")
    conflicting = _publish_request(
        command="msg_dispatch_nack",
    )

    initial = publisher.publish(first)
    conflict = publisher.publish(conflicting)

    assert initial.accepted is True
    assert conflict.accepted is False
    assert conflict.error_code == "communication_idempotency_conflict"
    records = publisher.list_message_records(task_id="task-wp3-001")
    assert len(records) == 1
