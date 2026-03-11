"""Communication dispatch adapter for governed ACP contract baseline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from openqilin.communication_gateway.delivery.publisher import (
    DeliveryPublisher,
    InMemoryDeliveryPublisher,
    PublishRequest,
)
from openqilin.data_access.repositories.communication import CommunicationMessageRecord
from openqilin.communication_gateway.transport.route_resolver import (
    RouteResolutionError,
    resolve_acp_route,
)
from openqilin.communication_gateway.validators.a2a_validator import (
    A2AValidationError,
    build_a2a_envelope,
    metadata_value,
)
from openqilin.communication_gateway.validators.ordering_validator import (
    InMemoryOrderingValidator,
    OrderingValidationError,
)


@dataclass(frozen=True, slots=True)
class CommunicationDispatchRequest:
    """Dispatch payload for communication gateway boundary."""

    task_id: str
    trace_id: str
    principal_id: str
    connector: str
    command: str
    target: str
    args: tuple[str, ...]
    idempotency_key: str
    project_id: str | None
    created_at: datetime
    metadata: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class CommunicationDispatchReceipt:
    """Communication dispatch boundary receipt."""

    accepted: bool
    dispatch_id: str | None
    error_code: str | None
    message: str
    route_key: str | None
    retryable: bool = False


class CommunicationDispatchAdapter(Protocol):
    """Communication dispatch adapter protocol."""

    def dispatch(self, payload: CommunicationDispatchRequest) -> CommunicationDispatchReceipt:
        """Dispatch admitted communication task through ACP contract boundary."""


class InMemoryCommunicationDispatchAdapter:
    """Deterministic ACP baseline adapter with A2A/ordering contract checks."""

    def __init__(
        self,
        ordering_validator: InMemoryOrderingValidator | None = None,
        publisher: DeliveryPublisher | None = None,
    ) -> None:
        self._ordering_validator = ordering_validator or InMemoryOrderingValidator()
        self._publisher = publisher or InMemoryDeliveryPublisher()

    def dispatch(self, payload: CommunicationDispatchRequest) -> CommunicationDispatchReceipt:
        """Validate A2A baseline contract and resolve ACP route before accept."""

        metadata = dict(payload.metadata)
        try:
            envelope = build_a2a_envelope(
                message_id=metadata_value(metadata, "message_id"),
                external_message_id=metadata_value(metadata, "external_message_id"),
                trace_id=payload.trace_id,
                principal_id=payload.principal_id,
                connector=payload.connector,
                command=payload.command,
                target=payload.target,
                args=payload.args,
                idempotency_key=payload.idempotency_key,
                project_id=payload.project_id,
                created_at=payload.created_at,
            )
            self._ordering_validator.validate(envelope)
            route = resolve_acp_route(envelope)
        except (A2AValidationError, OrderingValidationError, RouteResolutionError) as error:
            return CommunicationDispatchReceipt(
                accepted=False,
                dispatch_id=None,
                error_code=error.code,
                message=error.message,
                route_key=None,
                retryable=False,
            )
        publish_receipt = self._publisher.publish(
            PublishRequest(
                task_id=payload.task_id,
                trace_id=payload.trace_id,
                message_id=envelope.message_id,
                external_message_id=envelope.external_message_id,
                connector=envelope.connector,
                command=envelope.command,
                target=envelope.target,
                args=envelope.args,
                route_key=route.route_key,
                endpoint=route.endpoint,
            )
        )
        if publish_receipt.accepted:
            return CommunicationDispatchReceipt(
                accepted=True,
                dispatch_id=publish_receipt.dispatch_id,
                error_code=None,
                message=publish_receipt.message,
                route_key=publish_receipt.route_key,
                retryable=False,
            )
        return CommunicationDispatchReceipt(
            accepted=False,
            dispatch_id=None,
            error_code=publish_receipt.error_code,
            message=publish_receipt.message,
            route_key=publish_receipt.route_key,
            retryable=publish_receipt.retryable,
        )

    def list_message_records(
        self,
        *,
        task_id: str | None = None,
    ) -> tuple[CommunicationMessageRecord, ...]:
        """List persisted communication message records for diagnostics/tests."""

        publisher = self._publisher
        if isinstance(publisher, InMemoryDeliveryPublisher):
            return publisher.list_message_records(task_id=task_id)
        return ()
