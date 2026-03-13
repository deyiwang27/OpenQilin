from __future__ import annotations

from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def test_owner_command_denied_when_discord_context_missing() -> None:
    client = TestClient(create_control_plane_app())
    payload = build_owner_command_request_dict(
        action="run_task",
        args=["smoke"],
        actor_id="owner_m7_wp2_001",
        idempotency_key="idem-m7-wp2-001",
        trace_id="trace-m7-wp2-001",
        target="sandbox",
    )
    payload["connector"].pop("discord_context", None)

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    assert response.status_code == 422


def test_owner_command_denied_when_identity_channel_mapping_revoked() -> None:
    app = create_control_plane_app()
    services = app.state.runtime_services
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=["agent_m7_wp2"],
        actor_id="owner_m7_wp2_002",
        idempotency_key="idem-m7-wp2-002",
        trace_id="trace-m7-wp2-002",
        target="communication",
    )
    context = payload["connector"]["discord_context"]
    services.identity_channel_repo.claim_mapping(
        connector="discord",
        actor_external_id=payload["connector"]["actor_external_id"],
        guild_id=context["guild_id"],
        channel_id=context["channel_id"],
        channel_type=context["channel_type"],
    )
    services.identity_channel_repo.set_mapping_status(
        connector="discord",
        actor_external_id=payload["connector"]["actor_external_id"],
        guild_id=context["guild_id"],
        channel_id=context["channel_id"],
        channel_type=context["channel_type"],
        status="revoked",
    )
    client = TestClient(app)

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )
    body = response.json()

    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "connector_identity_channel_revoked"


def test_owner_command_denied_when_project_chat_is_read_only() -> None:
    app = create_control_plane_app()
    services = app.state.runtime_services
    project = services.governance_repo.create_project(
        project_id="project_m7_wp3_read_only",
        name="M7 WP3 read-only project",
        objective="validate project chat lifecycle gate",
    )
    services.governance_repo.transition_project_status(
        project_id=project.project_id,
        next_status="approved",
        reason_code="triad_approval",
        actor_role="ceo",
        trace_id="trace-m7-wp3-001",
    )
    services.governance_repo.transition_project_status(
        project_id=project.project_id,
        next_status="active",
        reason_code="start",
        actor_role="cwo",
        trace_id="trace-m7-wp3-002",
    )
    services.governance_repo.transition_project_status(
        project_id=project.project_id,
        next_status="completed",
        reason_code="complete",
        actor_role="project_manager",
        trace_id="trace-m7-wp3-003",
    )
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=["agent_m7_wp3"],
        actor_id="owner_m7_wp3_001",
        idempotency_key="idem-m7-wp3-001",
        trace_id="trace-m7-wp3-004",
        target="communication",
        project_id=project.project_id,
        discord_chat_class="project",
    )

    response = TestClient(app).post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )
    body = response.json()

    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_project_channel_read_only"


def test_owner_command_denied_when_pending_role_is_addressed() -> None:
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=["domain_leader_01"],
        actor_id="owner_m7_wp3_002",
        idempotency_key="idem-m7-wp3-010",
        trace_id="trace-m7-wp3-010",
        target="communication",
        recipients=[{"recipient_id": "domain_leader_01", "recipient_type": "domain_leader"}],
        discord_chat_class="project",
    )

    response = TestClient(create_control_plane_app()).post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )
    body = response.json()

    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_chat_role_pending_activation"
