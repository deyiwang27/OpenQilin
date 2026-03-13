from __future__ import annotations

from typing import Mapping

from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.testing.governance_api import build_governance_headers


def _post_governance(
    *,
    client: TestClient,
    path: str,
    actor_id: str,
    actor_role: str,
    payload: Mapping[str, object],
):
    return client.post(
        path,
        headers=build_governance_headers(
            payload=payload,
            actor_id=actor_id,
            actor_role=actor_role,
        ),
        json=dict(payload),
    )


def _seed_active_project(*, client: TestClient, project_id: str) -> None:
    create_payload = {
        "trace_id": f"trace-{project_id}-create",
        "project_id": project_id,
        "name": "M8 WP2 Lifecycle Router",
        "objective": "Seed active lifecycle state for governed transitions.",
        "metadata": {"suite": "component"},
    }
    create_response = _post_governance(
        client=client,
        path="/v1/governance/projects",
        actor_id="owner_1",
        actor_role="owner",
        payload=create_payload,
    )
    assert create_response.status_code == 201

    for role in ("owner", "ceo", "cwo"):
        approve_payload = {"trace_id": f"trace-{project_id}-approve-{role}"}
        approve_response = _post_governance(
            client=client,
            path=f"/v1/governance/projects/{project_id}/proposal/approve",
            actor_id=f"{role}_1",
            actor_role=role,
            payload=approve_payload,
        )
        assert approve_response.status_code == 200

    initialize_payload = {
        "trace_id": f"trace-{project_id}-initialize",
        "objective": "Active lifecycle seed",
        "budget_currency_total": 120.0,
        "budget_quota_total": 1200.0,
        "metric_plan": {"delivery": "green"},
        "workforce_plan": {"project_manager": "1"},
    }
    initialize_response = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/initialize",
        actor_id="cwo_1",
        actor_role="cwo",
        payload=initialize_payload,
    )
    assert initialize_response.status_code == 200


def test_pause_project_allows_project_manager_and_emits_audit_event() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    project_id = "project_m8_wp2_pause"
    _seed_active_project(client=client, project_id=project_id)

    payload = {
        "trace_id": "trace-m8-wp2-pause",
        "reason_code": "pm_status_report_replan",
    }
    response = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/lifecycle/pause",
        actor_id="pm_1",
        actor_role="project_manager",
        payload=payload,
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["previous_status"] == "active"
    assert body["data"]["status"] == "paused"

    events = app.state.runtime_services.audit_writer.get_events()
    paused_event = next(event for event in events if event.event_type == "project.paused")
    paused_payload = dict(paused_event.payload)
    assert paused_event.trace_id == payload["trace_id"]
    assert paused_payload["project_id"] == project_id
    assert paused_payload["status"] == "paused"
    assert paused_payload["previous_status"] == "active"


def test_resume_project_requires_paused_state_and_returns_active() -> None:
    client = TestClient(create_control_plane_app())
    project_id = "project_m8_wp2_resume"
    _seed_active_project(client=client, project_id=project_id)

    pause_payload = {
        "trace_id": "trace-m8-wp2-resume-pause",
        "reason_code": "pm_replan_pause",
    }
    pause_response = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/lifecycle/pause",
        actor_id="pm_1",
        actor_role="project_manager",
        payload=pause_payload,
    )
    assert pause_response.status_code == 200

    resume_payload = {
        "trace_id": "trace-m8-wp2-resume",
        "reason_code": "pm_resume_after_replan",
    }
    resume_response = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/lifecycle/resume",
        actor_id="pm_1",
        actor_role="project_manager",
        payload=resume_payload,
    )

    body = resume_response.json()
    assert resume_response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["previous_status"] == "paused"
    assert body["data"]["status"] == "active"


def test_terminate_project_allows_c_suite_only() -> None:
    client = TestClient(create_control_plane_app())
    project_id = "project_m8_wp2_terminate"
    _seed_active_project(client=client, project_id=project_id)

    payload = {
        "trace_id": "trace-m8-wp2-terminate",
        "reason_code": "terminated_by_cwo_decision",
    }
    response = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/lifecycle/terminate",
        actor_id="cwo_1",
        actor_role="cwo",
        payload=payload,
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["previous_status"] == "active"
    assert body["data"]["status"] == "terminated"


def test_archive_project_allows_terminated_to_archived_transition() -> None:
    client = TestClient(create_control_plane_app())
    project_id = "project_m8_wp2_archive"
    _seed_active_project(client=client, project_id=project_id)

    terminate_payload = {
        "trace_id": "trace-m8-wp2-archive-terminate",
        "reason_code": "terminated_by_cwo_decision",
    }
    terminate_response = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/lifecycle/terminate",
        actor_id="cwo_1",
        actor_role="cwo",
        payload=terminate_payload,
    )
    assert terminate_response.status_code == 200

    archive_payload = {
        "trace_id": "trace-m8-wp2-archive",
        "reason_code": "archive_after_termination",
    }
    archive_response = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/lifecycle/archive",
        actor_id="ceo_1",
        actor_role="ceo",
        payload=archive_payload,
    )

    body = archive_response.json()
    assert archive_response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["previous_status"] == "terminated"
    assert body["data"]["status"] == "archived"


def test_lifecycle_routes_reject_forbidden_role_and_invalid_transition() -> None:
    client = TestClient(create_control_plane_app())
    project_id = "project_m8_wp2_denied"
    _seed_active_project(client=client, project_id=project_id)

    forbidden_payload = {
        "trace_id": "trace-m8-wp2-forbidden",
        "reason_code": "owner_attempt_terminate",
    }
    forbidden = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/lifecycle/terminate",
        actor_id="owner_1",
        actor_role="owner",
        payload=forbidden_payload,
    )
    forbidden_body = forbidden.json()
    assert forbidden.status_code == 403
    assert forbidden_body["status"] == "denied"
    assert forbidden_body["error"]["code"] == "governance_project_lifecycle_role_forbidden"

    invalid_payload = {
        "trace_id": "trace-m8-wp2-invalid-transition",
        "reason_code": "archive_before_termination_or_completion",
    }
    invalid = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/lifecycle/archive",
        actor_id="ceo_1",
        actor_role="ceo",
        payload=invalid_payload,
    )
    invalid_body = invalid.json()
    assert invalid.status_code == 409
    assert invalid_body["status"] == "denied"
    assert invalid_body["error"]["code"] == "project_invalid_transition"
