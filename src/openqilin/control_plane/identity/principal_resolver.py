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


def resolve_principal(headers: Mapping[str, str]) -> Principal:
    """Resolve principal identity from HTTP headers."""

    principal_id = _required_header(headers, "x-openqilin-user-id")
    connector = _required_header(headers, "x-openqilin-connector")
    return Principal(principal_id=principal_id, connector=connector)
