import pytest

from openqilin.control_plane.identity.principal_resolver import (
    PrincipalResolutionError,
    resolve_principal,
)
from openqilin.control_plane.schemas.owner_commands import OwnerCommandRequest
from openqilin.task_orchestrator.admission.envelope_validator import (
    EnvelopeValidationError,
    validate_owner_command_envelope,
)


def test_resolve_principal_success() -> None:
    principal = resolve_principal(
        {
            "x-openqilin-user-id": "owner_123",
            "x-openqilin-connector": "discord",
        }
    )

    assert principal.principal_id == "owner_123"
    assert principal.connector == "discord"


def test_resolve_principal_missing_required_header() -> None:
    with pytest.raises(PrincipalResolutionError) as exc:
        resolve_principal({"x-openqilin-user-id": "owner_123"})

    assert exc.value.code == "principal_missing_header"


def test_validate_owner_command_envelope_success() -> None:
    payload = OwnerCommandRequest(
        command=" run_task ",
        args=[" alpha ", "beta"],
        idempotency_key="idem-12345678",
    )
    principal = resolve_principal(
        {
            "x-openqilin-user-id": "owner_123",
            "x-openqilin-connector": "discord",
        }
    )

    envelope = validate_owner_command_envelope(
        payload=payload,
        principal=principal,
        trace_id="trace-1",
    )

    assert envelope.request_id
    assert envelope.trace_id == "trace-1"
    assert envelope.command == "run_task"
    assert envelope.args == ("alpha", "beta")


def test_validate_owner_command_envelope_rejects_blank_args() -> None:
    payload = OwnerCommandRequest(
        command="run_task",
        args=["alpha", "  "],
        idempotency_key="idem-12345678",
    )
    principal = resolve_principal(
        {
            "x-openqilin-user-id": "owner_123",
            "x-openqilin-connector": "discord",
        }
    )

    with pytest.raises(EnvelopeValidationError) as exc:
        validate_owner_command_envelope(
            payload=payload,
            principal=principal,
            trace_id="trace-1",
        )

    assert exc.value.code == "envelope_invalid_args"
