import pytest

from openqilin.control_plane.identity.principal_resolver import (
    PrincipalResolutionError,
    resolve_principal,
)
from openqilin.task_orchestrator.admission.envelope_validator import (
    EnvelopeValidationError,
    validate_owner_command_envelope,
)
from openqilin.testing.owner_command import build_owner_command_request_model


def test_resolve_principal_success() -> None:
    principal = resolve_principal(
        {
            "x-external-channel": "discord",
            "x-openqilin-actor-external-id": "owner_123",
        }
    )

    assert principal.principal_id == "owner_123"
    assert principal.connector == "discord"
    assert principal.principal_role == "owner"


def test_resolve_principal_missing_required_header() -> None:
    with pytest.raises(PrincipalResolutionError) as exc:
        resolve_principal({"x-openqilin-actor-external-id": "owner_123"})

    assert exc.value.code == "principal_missing_header"


def test_validate_owner_command_envelope_success() -> None:
    payload = build_owner_command_request_model(
        action=" run_task ",
        args=[" alpha ", "beta"],
        actor_id="owner_123",
        idempotency_key="idem-12345678",
        trace_id="trace-1",
    )
    principal = resolve_principal(
        {
            "x-external-channel": "discord",
            "x-openqilin-actor-external-id": "owner_123",
        }
    )

    envelope = validate_owner_command_envelope(payload=payload, principal=principal)

    assert envelope.request_id
    assert envelope.trace_id == "trace-1"
    assert envelope.command == "run_task"
    assert envelope.target == "sandbox"
    assert envelope.args == ("alpha", "beta")
    assert dict(envelope.metadata)["recipient_types"] == "runtime"


def test_validate_owner_command_envelope_rejects_blank_args() -> None:
    payload = build_owner_command_request_model(
        action="run_task",
        args=["alpha", "  "],
        actor_id="owner_123",
        idempotency_key="idem-12345678",
        trace_id="trace-1",
    )
    principal = resolve_principal(
        {
            "x-external-channel": "discord",
            "x-openqilin-actor-external-id": "owner_123",
        }
    )

    with pytest.raises(EnvelopeValidationError) as exc:
        validate_owner_command_envelope(payload=payload, principal=principal)

    assert exc.value.code == "envelope_invalid_args"
