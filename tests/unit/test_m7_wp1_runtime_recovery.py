"""M7-WP1: Startup recovery unit tests using in-memory stubs."""

from __future__ import annotations

from openqilin.control_plane.api.startup_recovery import payload_hash_for_task
from openqilin.control_plane.idempotency.ingress_dedupe import IngressDedupeStore
from openqilin.task_orchestrator.admission.envelope_validator import AdmissionEnvelope
from openqilin.task_orchestrator.admission.service import AdmissionService
from tests.testing.infra_stubs import (
    InMemoryAgentRegistryRepository,
    InMemoryRuntimeStateRepository,
)

# Terminal task statuses for startup recovery counting (H-6: dispatched is NOT terminal).
_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled", "blocked"})

# Statuses that hold an idempotency claim during startup recovery (H-5: only active tasks).
_ACTIVE_STATUSES = frozenset({"queued", "dispatched", "running", "blocked"})


def _envelope(*, idempotency_key: str) -> AdmissionEnvelope:
    return AdmissionEnvelope(
        request_id="request-m7-wp1-001",
        trace_id="trace-m7-wp1-001",
        principal_id="owner_m7_001",
        principal_role="owner",
        trust_domain="discord",
        connector="discord",
        command="run_task_smoke",
        target="sandbox",
        args=("agent_runtime",),
        metadata=(
            ("external_message_id", "discord-msg-001"),
            ("message_id", "msg-001"),
            ("message_type", "owner_command"),
            ("priority", "normal"),
            ("raw_payload_hash", "hash-001"),
            ("recipient_ids", "agent_runtime"),
            ("recipient_types", "runtime"),
            ("sender_role", "owner"),
        ),
        project_id=None,
        idempotency_key=idempotency_key,
    )


def _run_startup_recovery(
    runtime_state_repo: InMemoryRuntimeStateRepository,
    ingress_dedupe: IngressDedupeStore,
) -> int:
    """Replicate the startup recovery ingress re-claim logic from build_runtime_services()."""
    reconstructed_ingress_claims = 0
    for task in runtime_state_repo.list_tasks():
        if task.status in _ACTIVE_STATUSES:
            status, _ = ingress_dedupe.claim(
                principal_id=task.principal_id,
                idempotency_key=task.idempotency_key,
                payload_hash=payload_hash_for_task(task),
            )
            ingress_dedupe.bind_task_id(
                principal_id=task.principal_id,
                idempotency_key=task.idempotency_key,
                task_id=task.task_id,
            )
            if status == "new":
                reconstructed_ingress_claims += 1
    return reconstructed_ingress_claims


def test_startup_recovery_rehydrates_task_state_and_ingress_idempotency() -> None:
    # First "boot": create and persist a task.
    first_repo = InMemoryRuntimeStateRepository()
    envelope = _envelope(idempotency_key="idem-m7-wp1-001")
    task = first_repo.create_task_from_envelope(envelope)
    first_repo.update_task_status(
        task.task_id,
        "blocked",
        outcome_source="policy_runtime",
        outcome_error_code="governance_denied",
        outcome_message="blocked for policy",
    )

    # "Second boot": use the same repo (simulating persistence) with new dedupe store.
    second_dedupe = IngressDedupeStore()
    reconstructed = _run_startup_recovery(first_repo, second_dedupe)

    # Blocked is in _ACTIVE_STATUSES so it gets re-claimed.
    all_tasks = first_repo.list_tasks()
    terminal_count = sum(1 for t in all_tasks if t.status in _TERMINAL_STATUSES)

    assert len(all_tasks) == 1
    assert terminal_count == 1  # blocked is terminal
    assert reconstructed == 1  # one blocked task re-claimed

    second_admission = AdmissionService(
        dedupe_store=second_dedupe,
        runtime_state_repo=first_repo,
    )
    replay = second_admission.admit_owner_command(envelope)
    assert replay.replayed is True
    assert replay.task.task_id == task.task_id
    assert replay.task.status == "blocked"


def test_startup_recovery_bootstraps_institutional_agents() -> None:
    agent_registry_repo = InMemoryAgentRegistryRepository()
    institutional_agents = agent_registry_repo.bootstrap_institutional_agents()
    roles = tuple(sorted(agent.role for agent in institutional_agents))

    assert roles == ("administrator", "auditor", "ceo", "cso", "cwo", "secretary")
