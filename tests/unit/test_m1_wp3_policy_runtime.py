from openqilin.control_plane.identity.principal_resolver import resolve_principal
from openqilin.data_access.repositories.runtime_state import (
    InMemoryRuntimeStateRepository,
    TaskRecord,
)
from openqilin.policy_runtime_integration.client import InMemoryPolicyRuntimeClient
from openqilin.policy_runtime_integration.fail_closed import evaluate_with_fail_closed
from openqilin.policy_runtime_integration.normalizer import normalize_policy_input
from openqilin.task_orchestrator.admission.envelope_validator import validate_owner_command_envelope
from openqilin.testing.owner_command import build_owner_command_request_model


def _build_task(command: str) -> TaskRecord:
    payload = build_owner_command_request_model(
        action=command,
        args=["alpha"],
        actor_id="owner_policy_001",
        idempotency_key=f"idem-{command}-12345678",
        trace_id="trace-policy-test",
    )
    principal = resolve_principal(
        {
            "x-external-channel": "discord",
            "x-openqilin-actor-external-id": "owner_policy_001",
        }
    )
    envelope = validate_owner_command_envelope(payload=payload, principal=principal)
    repository = InMemoryRuntimeStateRepository()
    return repository.create_task_from_envelope(envelope)


def test_normalize_policy_input_maps_task_fields() -> None:
    task = _build_task("run_task")

    policy_input = normalize_policy_input(task)

    assert policy_input.task_id == task.task_id
    assert policy_input.request_id == task.request_id
    assert policy_input.trace_id == task.trace_id
    assert policy_input.action == task.command


def test_policy_fail_closed_allows_on_allow_decision() -> None:
    task = _build_task("run_task")
    client = InMemoryPolicyRuntimeClient()

    outcome = evaluate_with_fail_closed(normalize_policy_input(task), client)

    assert outcome.allowed is True
    assert outcome.error_code is None
    assert outcome.policy_result is not None
    assert outcome.policy_result.decision == "allow"


def test_policy_fail_closed_blocks_on_deny_decision() -> None:
    task = _build_task("deny_delete_project")
    client = InMemoryPolicyRuntimeClient()

    outcome = evaluate_with_fail_closed(normalize_policy_input(task), client)

    assert outcome.allowed is False
    assert outcome.error_code == "policy_denied"
    assert outcome.policy_result is not None
    assert outcome.policy_result.decision == "deny"


def test_policy_fail_closed_blocks_on_uncertain_decision() -> None:
    task = _build_task("policy_uncertain")
    client = InMemoryPolicyRuntimeClient()

    outcome = evaluate_with_fail_closed(normalize_policy_input(task), client)

    assert outcome.allowed is False
    assert outcome.error_code == "policy_uncertain_fail_closed"
    assert outcome.policy_result is not None
    assert outcome.policy_result.decision == "uncertain"


def test_policy_fail_closed_blocks_on_runtime_error() -> None:
    task = _build_task("policy_error")
    client = InMemoryPolicyRuntimeClient()

    outcome = evaluate_with_fail_closed(normalize_policy_input(task), client)

    assert outcome.allowed is False
    assert outcome.error_code == "policy_runtime_error_fail_closed"
    assert outcome.policy_result is None
