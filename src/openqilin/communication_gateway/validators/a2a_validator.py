"""A2A envelope normalization and validation primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping


class A2AValidationError(ValueError):
    """Raised when A2A envelope data violates contract requirements."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class A2AEnvelope:
    """Canonical A2A envelope used by communication dispatch boundary."""

    schema_version: str
    message_id: str
    external_message_id: str
    trace_id: str
    principal_id: str
    connector: str
    command: str
    target: str
    args: tuple[str, ...]
    idempotency_key: str
    project_id: str | None
    created_at: datetime


def build_a2a_envelope(
    *,
    message_id: str,
    external_message_id: str,
    trace_id: str,
    principal_id: str,
    connector: str,
    command: str,
    target: str,
    args: tuple[str, ...],
    idempotency_key: str,
    project_id: str | None,
    created_at: datetime,
    schema_version: str = "a2a.v1",
) -> A2AEnvelope:
    """Build and validate canonical A2A envelope."""

    envelope = A2AEnvelope(
        schema_version=schema_version,
        message_id=message_id.strip(),
        external_message_id=external_message_id.strip(),
        trace_id=trace_id.strip(),
        principal_id=principal_id.strip(),
        connector=connector.strip(),
        command=command.strip(),
        target=target.strip(),
        args=tuple(arg.strip() for arg in args),
        idempotency_key=idempotency_key.strip(),
        project_id=project_id,
        created_at=created_at,
    )
    validate_a2a_envelope(envelope)
    return envelope


def validate_a2a_envelope(envelope: A2AEnvelope) -> None:
    """Validate A2A envelope contract for communication dispatch."""

    if envelope.schema_version != "a2a.v1":
        raise A2AValidationError(
            code="a2a_schema_unsupported",
            message="unsupported A2A schema version",
        )
    if not envelope.message_id:
        raise A2AValidationError(
            code="a2a_missing_message_id",
            message="missing message_id in A2A envelope",
        )
    if not envelope.external_message_id:
        raise A2AValidationError(
            code="a2a_missing_external_message_id",
            message="missing external_message_id in A2A envelope",
        )
    if not envelope.trace_id:
        raise A2AValidationError(
            code="a2a_missing_trace_id",
            message="missing trace_id in A2A envelope",
        )
    if not envelope.principal_id:
        raise A2AValidationError(
            code="a2a_missing_principal",
            message="missing principal in A2A envelope",
        )
    if envelope.connector not in {"discord", "internal"}:
        raise A2AValidationError(
            code="a2a_connector_unsupported",
            message="unsupported connector channel",
        )
    if not envelope.command.startswith("msg_"):
        raise A2AValidationError(
            code="a2a_invalid_command_type",
            message="communication dispatch requires msg_* command",
        )
    if not envelope.target:
        raise A2AValidationError(
            code="a2a_missing_target",
            message="missing communication target",
        )
    if not envelope.idempotency_key:
        raise A2AValidationError(
            code="a2a_missing_idempotency_key",
            message="missing idempotency_key in A2A envelope",
        )
    if not envelope.args:
        raise A2AValidationError(
            code="a2a_missing_recipient_args",
            message="communication command requires at least one recipient argument",
        )
    if any(not arg for arg in envelope.args):
        raise A2AValidationError(
            code="a2a_invalid_args",
            message="communication command args must not contain blank values",
        )


def metadata_value(metadata: Mapping[str, str], key: str) -> str:
    """Load required metadata value or raise contract error."""

    value = metadata.get(key, "").strip()
    if not value:
        raise A2AValidationError(
            code=f"a2a_missing_{key}",
            message=f"missing {key} in dispatch metadata",
        )
    return value
