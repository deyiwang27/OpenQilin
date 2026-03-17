from __future__ import annotations

import json

from fastapi.testclient import TestClient

from openqilin.apps.api_app import app
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def _ensure_active_project(*, project_id: str) -> None:
    services = app.state.runtime_services
    repository = services.governance_repo
    existing = repository.get_project(project_id)
    if existing is not None:
        return
    repository.create_project(
        project_id=project_id,
        name="M10 Tooling Project",
        objective="Validate governed tool writes",
        status="proposed",
    )
    repository.transition_project_status(
        project_id=project_id,
        next_status="approved",
        reason_code="seed_approved",
        actor_role="ceo",
        trace_id=f"trace-{project_id}-approved",
    )
    repository.transition_project_status(
        project_id=project_id,
        next_status="active",
        reason_code="seed_active",
        actor_role="cwo",
        trace_id=f"trace-{project_id}-active",
    )


def test_tool_write_accepts_governed_mutation_and_emits_audit_evidence() -> None:
    client = TestClient(app)
    project_id = "project_m10_tool_write_ok"
    _ensure_active_project(project_id=project_id)

    payload = build_owner_command_request_dict(
        action="tool_write",
        target="llm",
        args=[
            json.dumps(
                {
                    "tool": "append_progress_report",
                    "arguments": {
                        "project_id": project_id,
                        "content": "Weekly progress update: milestone A completed.",
                    },
                }
            )
        ],
        actor_id="owner_m10_tool_write_ok",
        actor_role="ceo",
        idempotency_key="idem-m10-tool-write-ok-001",
        project_id=project_id,
        recipients=[{"recipient_id": "ceo_core", "recipient_type": "ceo"}],
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["data"]["dispatch_target"] == "llm"
    assert body["data"]["llm_execution"]["generated_text"]
    assert "[source:artifact:progress_report]" in body["data"]["llm_execution"]["generated_text"]

    services = app.state.runtime_services
    assert any(
        event.event_type == "tool.write.append_progress_report"
        for event in services.audit_writer.get_events()
    )


def test_tool_write_denies_raw_mutation_requests_fail_closed() -> None:
    client = TestClient(app)
    project_id = "project_m10_tool_write_raw_denied"
    _ensure_active_project(project_id=project_id)

    payload = build_owner_command_request_dict(
        action="tool_write",
        target="llm",
        args=[
            json.dumps(
                {
                    "tool": "raw_sql_update",
                    "arguments": {
                        "project_id": project_id,
                        "statement": "UPDATE projects SET status='archived'",
                    },
                }
            )
        ],
        actor_id="owner_m10_tool_write_raw_denied",
        idempotency_key="idem-m10-tool-write-raw-denied-001",
        project_id=project_id,
        recipients=[{"recipient_id": "ceo_core", "recipient_type": "ceo"}],
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "tool_raw_db_mutation_denied"


def test_tool_read_denies_disallowed_role_tool_access() -> None:
    client = TestClient(app)
    project_id = "project_m10_tool_read_denied"
    _ensure_active_project(project_id=project_id)

    payload = build_owner_command_request_dict(
        action="tool_read",
        target="llm",
        args=[
            json.dumps(
                {
                    "tool": "get_audit_event_stream",
                    "arguments": {"project_id": project_id, "limit": 10},
                }
            )
        ],
        actor_id="owner_m10_tool_read_denied",
        idempotency_key="idem-m10-tool-read-denied-001",
        project_id=project_id,
        recipients=[{"recipient_id": "pm_core", "recipient_type": "project_manager"}],
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "tool_access_denied"
