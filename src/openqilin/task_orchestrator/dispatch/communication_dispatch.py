"""Communication dispatch adapter for governed ACP contract baseline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

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


class CommunicationDispatchAdapter(Protocol):
    """Communication dispatch adapter protocol."""

    def dispatch(self, payload: CommunicationDispatchRequest) -> CommunicationDispatchReceipt:
        """Dispatch admitted communication task through ACP contract boundary."""


class InMemoryCommunicationDispatchAdapter:
    """Deterministic ACP baseline adapter with A2A/ordering contract checks."""

    def __init__(self, ordering_validator: InMemoryOrderingValidator | None = None) -> None:
        self._ordering_validator = ordering_validator or InMemoryOrderingValidator()

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
            )

        if payload.command == "msg_dispatch_reject":
            return CommunicationDispatchReceipt(
                accepted=False,
                dispatch_id=None,
                error_code="acp_contract_rejected",
                message="ACP contract rejected communication payload",
                route_key=route.route_key,
            )

        return CommunicationDispatchReceipt(
            accepted=True,
            dispatch_id=f"acp-{uuid4()}",
            error_code=None,
            message=f"ACP contract accepted via {route.route_key}",
            route_key=route.route_key,
        )
