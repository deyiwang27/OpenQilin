"""Principal resolution utilities for governed ingress."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


class PrincipalResolutionError(ValueError):
    """Raised when inbound identity headers are missing or malformed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class Principal:
    """Normalized principal identity for admission flow."""

    principal_id: str
    connector: str
    principal_role: str
    trust_domain: str


def _required_header(headers: Mapping[str, str], header_name: str) -> str:
    value = headers.get(header_name)
    if value is None:
        raise PrincipalResolutionError(
            code="principal_missing_header",
            message=f"missing required header: {header_name}",
        )

    normalized = value.strip()
    if not normalized:
        raise PrincipalResolutionError(
            code="principal_invalid_header",
            message=f"header has empty value: {header_name}",
        )
    return normalized


def _optional_header(headers: Mapping[str, str], header_name: str) -> str | None:
    value = headers.get(header_name)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def resolve_principal(headers: Mapping[str, str]) -> Principal:
    """Resolve principal identity from connector-originated HTTP headers."""

    connector = _optional_header(headers, "x-external-channel") or _optional_header(
        headers, "x-openqilin-connector"
    )
    if connector is None:
        raise PrincipalResolutionError(
            code="principal_missing_header",
            message="missing required header: x-external-channel",
        )
    if connector not in {"discord", "internal"}:
        raise PrincipalResolutionError(
            code="principal_invalid_connector",
            message=f"unsupported connector: {connector}",
        )

    actor_external_id = (
        _optional_header(headers, "x-openqilin-actor-external-id")
        or _optional_header(headers, "x-external-actor-id")
        or _optional_header(headers, "x-openqilin-user-id")
    )
    if actor_external_id is None:
        raise PrincipalResolutionError(
            code="principal_missing_header",
            message=(
                "missing required header: x-openqilin-actor-external-id (or x-external-actor-id)"
            ),
        )

    principal_role = _optional_header(headers, "x-openqilin-actor-role") or "owner"
    trust_domain = "internal" if connector == "internal" else "external_verified"
    principal_id = actor_external_id
    return Principal(
        principal_id=principal_id,
        connector=connector,
        principal_role=principal_role,
        trust_domain=trust_domain,
    )
