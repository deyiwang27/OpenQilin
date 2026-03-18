"""Communication dispatch adapter for governed ACP contract baseline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from openqilin.communication_gateway.delivery.publisher import (
    DeliveryPublisher,
    LocalDeliveryPublisher,
    PublishRequest,
)
from openqilin.communication_gateway.storage.idempotency_store import CommunicationIdempotencyRecord
from openqilin.data_access.repositories.communication import (
    CommunicationDeadLetterRecord,
    CommunicationMessageRecord,
)
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
    LocalOrderingValidator,
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
    dead_letter_id: str | None = None


class CommunicationDispatchAdapter(Protocol):
    """Communication dispatch adapter protocol."""

    def dispatch(self, payload: CommunicationDispatchRequest) -> CommunicationDispatchReceipt:
        """Dispatch admitted communication task through ACP contract boundary."""


class LocalCommunicationDispatchAdapter:
    """Deterministic ACP baseline adapter with A2A/ordering contract checks."""

    def __init__(
        self,
        ordering_validator: LocalOrderingValidator | None = None,
        publisher: DeliveryPublisher | None = None,
    ) -> None:
        self._ordering_validator = ordering_validator or LocalOrderingValidator()
        self._publisher = publisher or LocalDeliveryPublisher()

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
                principal_id=payload.principal_id,
                idempotency_key=payload.idempotency_key,
                message_id=envelope.message_id,
                external_message_id=envelope.external_message_id,
                connector=envelope.connector,
                command=envelope.command,
                target=envelope.target,
                args=envelope.args,
                project_id=envelope.project_id,
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
                dead_letter_id=publish_receipt.dead_letter_id,
            )
        return CommunicationDispatchReceipt(
            accepted=False,
            dispatch_id=None,
            error_code=publish_receipt.error_code,
            message=publish_receipt.message,
            route_key=publish_receipt.route_key,
            retryable=publish_receipt.retryable,
            dead_letter_id=publish_receipt.dead_letter_id,
        )

    def list_message_records(
        self,
        *,
        task_id: str | None = None,
    ) -> tuple[CommunicationMessageRecord, ...]:
        """List persisted communication message records for diagnostics/tests."""

        publisher = self._publisher
        if isinstance(publisher, LocalDeliveryPublisher):
            return publisher.list_message_records(task_id=task_id)
        return ()

    def list_idempotency_records(self) -> tuple[CommunicationIdempotencyRecord, ...]:
        """List communication idempotency records for diagnostics/tests."""

        publisher = self._publisher
        if isinstance(publisher, LocalDeliveryPublisher):
            return publisher.list_idempotency_records()
        return ()

    def list_dead_letters(self) -> tuple[CommunicationDeadLetterRecord, ...]:
        """List communication dead-letter records for diagnostics/tests."""

        publisher = self._publisher
        if isinstance(publisher, LocalDeliveryPublisher):
            return publisher.list_dead_letters()
        return ()


# Backward-compatible alias retained for existing imports.
InMemoryCommunicationDispatchAdapter = LocalCommunicationDispatchAdapter
