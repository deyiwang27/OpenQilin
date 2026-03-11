"""Admission envelope normalization for owner command ingress."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from openqilin.control_plane.identity.principal_resolver import Principal
from openqilin.control_plane.schemas.owner_commands import OwnerCommandRequest


class EnvelopeValidationError(ValueError):
    """Raised when inbound envelope data is semantically invalid."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class AdmissionEnvelope:
    """Normalized envelope passed from control-plane to admission service."""

    request_id: str
    trace_id: str
    principal_id: str
    connector: str
    command: str
    args: tuple[str, ...]
    idempotency_key: str


def validate_owner_command_envelope(
    payload: OwnerCommandRequest,
    principal: Principal,
    trace_id: str,
) -> AdmissionEnvelope:
    """Validate and normalize ingress payload for downstream admission."""

    normalized_command = payload.command.strip()
    if not normalized_command:
        raise EnvelopeValidationError(
            code="envelope_invalid_command",
            message="command must not be blank",
        )

    normalized_args = tuple(arg.strip() for arg in payload.args)
    if any(not arg for arg in normalized_args):
        raise EnvelopeValidationError(
            code="envelope_invalid_args",
            message="args must not contain blank values",
        )

    normalized_trace_id = trace_id.strip()
    if not normalized_trace_id:
        raise EnvelopeValidationError(
            code="envelope_invalid_trace_id",
            message="trace identifier must not be blank",
        )

    return AdmissionEnvelope(
        request_id=str(uuid4()),
        trace_id=normalized_trace_id,
        principal_id=principal.principal_id,
        connector=principal.connector,
        command=normalized_command,
        args=normalized_args,
        idempotency_key=payload.idempotency_key,
    )
