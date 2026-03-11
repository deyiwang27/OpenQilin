"""ACP route resolution for validated communication envelopes."""

from __future__ import annotations

from dataclasses import dataclass

from openqilin.communication_gateway.validators.a2a_validator import A2AEnvelope


class RouteResolutionError(ValueError):
    """Raised when no ACP route can be resolved for envelope."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class AcpRoute:
    """Resolved ACP routing target."""

    route_key: str
    endpoint: str
    connector: str


def resolve_acp_route(envelope: A2AEnvelope) -> AcpRoute:
    """Resolve ACP route from envelope connector/target contract."""

    if envelope.connector == "discord":
        return AcpRoute(
            route_key="discord_direct_message",
            endpoint=f"acp://discord/{envelope.target}",
            connector=envelope.connector,
        )
    if envelope.connector == "internal":
        return AcpRoute(
            route_key="internal_bus_message",
            endpoint=f"acp://internal/{envelope.target}",
            connector=envelope.connector,
        )
    raise RouteResolutionError(
        code="acp_route_unmapped_connector",
        message="no ACP route mapping for connector",
    )
