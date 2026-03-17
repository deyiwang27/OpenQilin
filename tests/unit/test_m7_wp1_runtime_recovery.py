from __future__ import annotations

from openqilin.control_plane.api.dependencies import build_runtime_services
from openqilin.task_orchestrator.admission.envelope_validator import AdmissionEnvelope


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


def test_startup_recovery_rehydrates_task_state_and_ingress_idempotency(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("OPENQILIN_SYSTEM_ROOT", str(tmp_path / "system_root"))
    monkeypatch.setenv("OPENQILIN_RUNTIME_PERSISTENCE_ENABLED", "true")

    first = build_runtime_services()
    envelope = _envelope(idempotency_key="idem-m7-wp1-001")
    task = first.runtime_state_repo.create_task_from_envelope(envelope)
    first.runtime_state_repo.update_task_status(
        task.task_id,
        "blocked",
        outcome_source="policy_runtime",
        outcome_error_code="governance_denied",
        outcome_message="blocked for policy",
    )

    second = build_runtime_services()
    report = second.startup_recovery_report

    assert report.restored_task_count == 1
    assert report.restored_terminal_task_count == 1
    assert report.reconstructed_ingress_claims == 1
    assert report.institutional_agent_count == 5  # administrator, auditor, ceo, cwo, cso

    replay = second.admission_service.admit_owner_command(envelope)
    assert replay.replayed is True
    assert replay.task.task_id == task.task_id
    assert replay.task.status == "blocked"


def test_startup_recovery_bootstraps_institutional_agents(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OPENQILIN_SYSTEM_ROOT", str(tmp_path / "system_root"))
    monkeypatch.setenv("OPENQILIN_RUNTIME_PERSISTENCE_ENABLED", "true")

    services = build_runtime_services()
    roles = tuple(sorted(agent.role for agent in services.agent_registry_repo.list_agents()))

    assert roles == ("administrator", "auditor", "ceo", "cso", "cwo")
