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
    principal_role: str
    trust_domain: str
    connector: str
    command: str
    target: str
    args: tuple[str, ...]
    metadata: tuple[tuple[str, str], ...]
    project_id: str | None
    idempotency_key: str


def validate_owner_command_envelope(
    payload: OwnerCommandRequest,
    principal: Principal,
    trace_id_override: str | None = None,
) -> AdmissionEnvelope:
    """Validate and normalize ingress payload for downstream admission."""

    normalized_command = payload.command.action.strip()
    if not normalized_command:
        raise EnvelopeValidationError(
            code="envelope_invalid_command",
            message="command must not be blank",
        )

    normalized_target = payload.command.target.strip()
    if not normalized_target:
        raise EnvelopeValidationError(
            code="envelope_invalid_target",
            message="command target must not be blank",
        )

    raw_args = payload.command.payload.get("args", [])
    if not isinstance(raw_args, list):
        raise EnvelopeValidationError(
            code="envelope_invalid_args",
            message="command payload args must be a list of strings",
        )
    normalized_args = tuple(str(arg).strip() for arg in raw_args)
    if any(not arg for arg in normalized_args):
        raise EnvelopeValidationError(
            code="envelope_invalid_args",
            message="args must not contain blank values",
        )

    if payload.sender.actor_id.strip() != principal.principal_id:
        raise EnvelopeValidationError(
            code="envelope_sender_mismatch",
            message="sender actor_id does not match resolved principal",
        )

    normalized_trace_id = (trace_id_override or payload.trace_id).strip()
    if not normalized_trace_id:
        raise EnvelopeValidationError(
            code="envelope_invalid_trace_id",
            message="trace identifier must not be blank",
        )
    normalized_recipient_types = sorted(
        {
            recipient.recipient_type.strip().lower()
            for recipient in payload.recipients
            if recipient.recipient_type.strip()
        }
    )
    normalized_recipient_ids = sorted(
        {
            recipient.recipient_id.strip()
            for recipient in payload.recipients
            if recipient.recipient_id.strip()
        }
    )

    return AdmissionEnvelope(
        request_id=str(uuid4()),
        trace_id=normalized_trace_id,
        principal_id=principal.principal_id,
        principal_role=principal.principal_role,
        trust_domain=principal.trust_domain,
        connector=principal.connector,
        command=normalized_command,
        target=normalized_target,
        args=normalized_args,
        metadata=tuple(
            sorted(
                {
                    "message_id": payload.message_id,
                    "message_type": payload.message_type,
                    "priority": payload.priority,
                    "sender_role": payload.sender.actor_role,
                    "external_message_id": payload.connector.external_message_id,
                    "raw_payload_hash": payload.connector.raw_payload_hash,
                    "recipient_types": ",".join(normalized_recipient_types),
                    "recipient_ids": ",".join(normalized_recipient_ids),
                }.items()
            )
        ),
        project_id=payload.project_id,
        idempotency_key=payload.connector.idempotency_key,
    )
