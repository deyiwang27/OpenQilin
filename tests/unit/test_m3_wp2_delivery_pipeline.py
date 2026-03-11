from datetime import UTC, datetime

from openqilin.communication_gateway.delivery.publisher import (
    InMemoryDeliveryPublisher,
    PublishRequest,
)
from openqilin.task_orchestrator.dispatch.communication_dispatch import (
    CommunicationDispatchRequest,
    InMemoryCommunicationDispatchAdapter,
)


def _publish_request(*, command: str) -> PublishRequest:
    return PublishRequest(
        task_id="task-wp2-001",
        trace_id="trace-wp2-001",
        message_id="msg-wp2-001",
        external_message_id="ext-wp2-001",
        connector="discord",
        command=command,
        target="communication",
        args=("agent_1",),
        route_key="discord_direct_message",
        endpoint="acp://discord/communication",
    )


def test_delivery_publisher_persists_send_ack_transitions() -> None:
    publisher = InMemoryDeliveryPublisher()

    receipt = publisher.publish(_publish_request(command="msg_notify"))

    assert receipt.accepted is True
    assert receipt.dispatch_id
    assert receipt.error_code is None
    record = publisher.get_message_record(receipt.ledger_id)
    assert record is not None
    assert record.state == "acked"
    assert record.retryable is False
    assert tuple(transition.state for transition in record.transitions) == (
        "prepared",
        "sent",
        "acked",
    )


def test_delivery_publisher_persists_send_nack_transitions() -> None:
    publisher = InMemoryDeliveryPublisher()

    receipt = publisher.publish(_publish_request(command="msg_dispatch_reject"))

    assert receipt.accepted is False
    assert receipt.dispatch_id is None
    assert receipt.error_code == "acp_contract_rejected"
    assert receipt.retryable is False
    record = publisher.get_message_record(receipt.ledger_id)
    assert record is not None
    assert record.state == "nacked"
    assert record.error_code == "acp_contract_rejected"
    assert record.retryable is False
    assert tuple(transition.state for transition in record.transitions) == (
        "prepared",
        "sent",
        "nacked",
    )


def test_delivery_publisher_marks_retryable_nack_on_transport_error() -> None:
    publisher = InMemoryDeliveryPublisher()

    receipt = publisher.publish(_publish_request(command="msg_transport_error"))

    assert receipt.accepted is False
    assert receipt.error_code == "acp_transport_unavailable"
    assert receipt.retryable is True
    record = publisher.get_message_record(receipt.ledger_id)
    assert record is not None
    assert record.state == "nacked"
    assert record.dispatch_id is None
    assert record.delivery_id is None
    assert record.error_code == "acp_transport_unavailable"
    assert record.retryable is True
    assert tuple(transition.state for transition in record.transitions) == (
        "prepared",
        "nacked",
    )


def test_communication_dispatch_adapter_returns_retryable_nack_metadata() -> None:
    adapter = InMemoryCommunicationDispatchAdapter()

    receipt = adapter.dispatch(
        CommunicationDispatchRequest(
            task_id="task-wp2-001",
            trace_id="trace-wp2-001",
            principal_id="owner-wp2-001",
            connector="discord",
            command="msg_dispatch_retryable_nack",
            target="communication",
            args=("agent_1",),
            idempotency_key="idem-wp2-001",
            project_id="project_1",
            created_at=datetime.now(tz=UTC),
            metadata=(
                ("message_id", "msg-wp2-001"),
                ("external_message_id", "ext-wp2-001"),
            ),
        )
    )

    assert receipt.accepted is False
    assert receipt.error_code == "acp_delivery_nack_retryable"
    assert receipt.retryable is True
    records = adapter.list_message_records(task_id="task-wp2-001")
    assert len(records) == 1
    assert records[0].state == "nacked"
    assert records[0].retryable is True
    assert tuple(transition.state for transition in records[0].transitions) == (
        "prepared",
        "sent",
        "nacked",
    )
