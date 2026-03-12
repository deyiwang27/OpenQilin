from datetime import UTC, datetime, timedelta

from openqilin.communication_gateway.transport.route_resolver import resolve_acp_route
from openqilin.communication_gateway.validators.a2a_validator import (
    A2AValidationError,
    build_a2a_envelope,
)
from openqilin.communication_gateway.validators.ordering_validator import (
    InMemoryOrderingValidator,
    OrderingValidationError,
)
from openqilin.task_orchestrator.dispatch.communication_dispatch import (
    CommunicationDispatchRequest,
    InMemoryCommunicationDispatchAdapter,
)


def _build_envelope(*, created_at: datetime | None = None):
    return build_a2a_envelope(
        message_id="msg-001",
        external_message_id="ext-001",
        trace_id="trace-001",
        principal_id="owner-001",
        connector="discord",
        command="msg_notify",
        target="communication",
        args=("agent_1",),
        idempotency_key="idem-001",
        project_id="project_1",
        created_at=created_at or datetime.now(tz=UTC),
    )


def test_build_a2a_envelope_accepts_valid_message() -> None:
    envelope = _build_envelope()

    assert envelope.schema_version == "a2a.v1"
    assert envelope.command == "msg_notify"
    assert envelope.args == ("agent_1",)


def test_build_a2a_envelope_rejects_missing_args() -> None:
    try:
        build_a2a_envelope(
            message_id="msg-001",
            external_message_id="ext-001",
            trace_id="trace-001",
            principal_id="owner-001",
            connector="discord",
            command="msg_notify",
            target="communication",
            args=(),
            idempotency_key="idem-001",
            project_id="project_1",
            created_at=datetime.now(tz=UTC),
        )
    except A2AValidationError as error:
        assert error.code == "a2a_missing_recipient_args"
    else:
        raise AssertionError("expected A2AValidationError")


def test_ordering_validator_rejects_duplicate_message_id() -> None:
    validator = InMemoryOrderingValidator()
    envelope = _build_envelope()

    validator.validate(envelope)
    try:
        validator.validate(envelope)
    except OrderingValidationError as error:
        assert error.code == "a2a_duplicate_message_id"
    else:
        raise AssertionError("expected OrderingValidationError")


def test_ordering_validator_rejects_out_of_order_timestamp() -> None:
    validator = InMemoryOrderingValidator()
    current = datetime.now(tz=UTC)
    newer = _build_envelope(created_at=current)
    older = build_a2a_envelope(
        message_id="msg-002",
        external_message_id="ext-002",
        trace_id="trace-001",
        principal_id="owner-001",
        connector="discord",
        command="msg_notify",
        target="communication",
        args=("agent_1",),
        idempotency_key="idem-002",
        project_id="project_1",
        created_at=current - timedelta(seconds=1),
    )

    validator.validate(newer)
    try:
        validator.validate(older)
    except OrderingValidationError as error:
        assert error.code == "a2a_out_of_order_delivery"
    else:
        raise AssertionError("expected OrderingValidationError")


def test_route_resolver_maps_discord_connector() -> None:
    route = resolve_acp_route(_build_envelope())

    assert route.route_key == "discord_direct_message"
    assert route.endpoint == "acp://discord/communication"


def test_communication_dispatch_adapter_accepts_valid_payload() -> None:
    adapter = InMemoryCommunicationDispatchAdapter()
    receipt = adapter.dispatch(
        CommunicationDispatchRequest(
            task_id="task-001",
            trace_id="trace-001",
            principal_id="owner-001",
            connector="discord",
            command="msg_notify",
            target="communication",
            args=("agent_1",),
            idempotency_key="idem-001",
            project_id="project_1",
            created_at=datetime.now(tz=UTC),
            metadata=(
                ("message_id", "msg-001"),
                ("external_message_id", "ext-001"),
            ),
        )
    )

    assert receipt.accepted is True
    assert receipt.dispatch_id
    assert receipt.route_key == "discord_direct_message"


def test_communication_dispatch_adapter_denies_missing_args() -> None:
    adapter = InMemoryCommunicationDispatchAdapter()
    receipt = adapter.dispatch(
        CommunicationDispatchRequest(
            task_id="task-001",
            trace_id="trace-001",
            principal_id="owner-001",
            connector="discord",
            command="msg_notify",
            target="communication",
            args=(),
            idempotency_key="idem-001",
            project_id="project_1",
            created_at=datetime.now(tz=UTC),
            metadata=(
                ("message_id", "msg-001"),
                ("external_message_id", "ext-001"),
            ),
        )
    )

    assert receipt.accepted is False
    assert receipt.error_code == "a2a_missing_recipient_args"
