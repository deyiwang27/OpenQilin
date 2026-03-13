from pathlib import Path
from typing import Any, Mapping, cast

from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.testing.governance_api import build_governance_headers
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


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


def _approve_project_by_triad(*, client: TestClient, project_id: str) -> None:
    for actor_role in ("owner", "ceo", "cwo"):
        payload = {"trace_id": f"trace-m7-wp6-approve-{actor_role}-{project_id}"}
        response = _post_governance(
            client=client,
            path=f"/v1/governance/projects/{project_id}/proposal/approve",
            actor_id=f"{actor_role}_m7_wp6",
            actor_role=actor_role,
            payload=payload,
        )
        assert response.status_code == 200


def _create_project(*, client: TestClient, project_id: str, name: str, objective: str) -> None:
    payload = {
        "trace_id": f"trace-m7-wp6-create-{project_id}",
        "project_id": project_id,
        "name": name,
        "objective": objective,
        "metadata": {"suite": "m7_wp6_acceptance"},
    }
    response = _post_governance(
        client=client,
        path="/v1/governance/projects",
        actor_id="owner_m7_wp6",
        actor_role="owner",
        payload=payload,
    )
    assert response.status_code == 201


def _initialize_active_project(*, client: TestClient, project_id: str) -> dict[str, object]:
    payload = {
        "trace_id": f"trace-m7-wp6-init-{project_id}",
        "objective": "Deliver governed MVP acceptance scenario",
        "budget_currency_total": 100.0,
        "budget_quota_total": 1000.0,
        "metric_plan": {"delivery": "all_acceptance_checks_green"},
        "workforce_plan": {"project_manager": "1", "specialist": "2"},
    }
    response = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/initialize",
        actor_id="cwo_m7_wp6",
        actor_role="cwo",
        payload=payload,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["status"] == "active"
    return body["data"]


def _bind_project_manager(*, client: TestClient, project_id: str) -> None:
    payload = {
        "trace_id": f"trace-m7-wp6-bind-{project_id}",
        "role": "project_manager",
        "template_id": "project_manager_template_v1",
        "llm_routing_profile": "dev_gemini_free",
        "system_prompt": (
            "You are Project Manager. Mandatory operations: milestone planning, "
            "task decomposition, task assignment, progress reporting."
        ),
    }
    response = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/workforce/bind",
        actor_id="cwo_m7_wp6",
        actor_role="cwo",
        payload=payload,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["binding_status"] == "active"


def _complete_project_via_governance_chain(*, client: TestClient, project_id: str) -> None:
    report_payload = {
        "trace_id": f"trace-m7-wp6-completion-report-{project_id}",
        "summary": "All acceptance checks are complete.",
        "metric_results": {"mvp_acceptance": "passed"},
    }
    report = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/completion/report",
        actor_id="pm_m7_wp6",
        actor_role="project_manager",
        payload=report_payload,
    )
    assert report.status_code == 201
    cwo_approval_payload = {"trace_id": f"trace-m7-wp6-completion-approval-cwo-{project_id}"}
    cwo_approval = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/completion/approve",
        actor_id="cwo_m7_wp6",
        actor_role="cwo",
        payload=cwo_approval_payload,
    )
    assert cwo_approval.status_code == 200
    ceo_approval_payload = {"trace_id": f"trace-m7-wp6-completion-approval-ceo-{project_id}"}
    ceo_approval = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/completion/approve",
        actor_id="ceo_m7_wp6",
        actor_role="ceo",
        payload=ceo_approval_payload,
    )
    assert ceo_approval.status_code == 200
    finalize_payload = {"trace_id": f"trace-m7-wp6-completion-finalize-{project_id}"}
    finalize = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/completion/finalize",
        actor_id="cwo_m7_wp6",
        actor_role="cwo",
        payload=finalize_payload,
    )
    assert finalize.status_code == 200
    assert finalize.json()["data"]["status"] == "completed"


def _transition_project_lifecycle(
    *,
    client: TestClient,
    project_id: str,
    action: str,
    actor_id: str,
    actor_role: str,
    trace_id: str,
    reason_code: str,
):
    payload = {
        "trace_id": trace_id,
        "reason_code": reason_code,
    }
    return _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/lifecycle/{action}",
        actor_id=actor_id,
        actor_role=actor_role,
        payload=payload,
    )


def _verify_discord_mapping(*, client: TestClient, actor_external_id: str, channel_id: str) -> None:
    app = cast(Any, client.app)
    services = cast(Any, app.state.runtime_services)
    identity_repo = services.identity_channel_repo
    identity_repo.claim_mapping(
        connector="discord",
        actor_external_id=actor_external_id,
        guild_id="guild-m7-wp6",
        channel_id=channel_id,
        channel_type="text",
    )
    identity_repo.set_mapping_status(
        connector="discord",
        actor_external_id=actor_external_id,
        guild_id="guild-m7-wp6",
        channel_id=channel_id,
        channel_type="text",
        status="verified",
    )


def _build_project_chat_payload(
    *, project_id: str, action: str, channel_id: str
) -> dict[str, object]:
    return build_owner_command_request_dict(
        action=action,
        args=["mvp", "acceptance"],
        actor_id="owner_m7_wp6",
        target="communication" if action.startswith("msg_") else "sandbox",
        project_id=project_id,
        discord_guild_id="guild-m7-wp6",
        discord_channel_id=channel_id,
        discord_chat_class="project",
        recipients=[{"recipient_id": "pm_m7_wp6", "recipient_type": "project_manager"}],
        content=f"m7 wp6 payload for {action}",
    )


def test_m7_wp6_acceptance_completed_archive_path_and_discord_read_controls(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("OPENQILIN_SYSTEM_ROOT", str(tmp_path / "openqilin-system"))
    app = create_control_plane_app()
    client = TestClient(app)
    _create_project(
        client=client,
        project_id="project_m7_wp6_completed",
        name="M7 WP6 Completed Path",
        objective="Validate completed->archived acceptance branch",
    )

    discussion_payload = {
        "trace_id": "trace-m7-wp6-discussion-completed",
        "content": "Propose MVP acceptance project and delivery criteria.",
    }
    discussion = _post_governance(
        client=client,
        path="/v1/governance/projects/project_m7_wp6_completed/proposal/messages",
        actor_id="owner_m7_wp6",
        actor_role="owner",
        payload=discussion_payload,
    )
    assert discussion.status_code == 201

    _approve_project_by_triad(client=client, project_id="project_m7_wp6_completed")
    init_data = _initialize_active_project(client=client, project_id="project_m7_wp6_completed")
    _bind_project_manager(client=client, project_id="project_m7_wp6_completed")

    charter_path = Path(str(init_data["charter_storage_uri"]))
    assert charter_path.exists()

    _verify_discord_mapping(
        client=client,
        actor_external_id="owner_m7_wp6",
        channel_id="channel-m7-wp6-project",
    )

    active_payload = _build_project_chat_payload(
        project_id="project_m7_wp6_completed",
        action="msg_send",
        channel_id="channel-m7-wp6-project",
    )
    active_response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(active_payload),
        json=active_payload,
    )
    assert active_response.status_code == 202
    assert active_response.json()["status"] == "accepted"

    pause_response = _transition_project_lifecycle(
        client=client,
        project_id="project_m7_wp6_completed",
        action="pause",
        actor_id="pm_m7_wp6",
        actor_role="project_manager",
        trace_id="trace-m7-wp6-pause",
        reason_code="pm_status_report_replan",
    )
    assert pause_response.status_code == 200
    assert pause_response.json()["data"]["status"] == "paused"

    resume_response = _transition_project_lifecycle(
        client=client,
        project_id="project_m7_wp6_completed",
        action="resume",
        actor_id="pm_m7_wp6",
        actor_role="project_manager",
        trace_id="trace-m7-wp6-resume",
        reason_code="pm_resume_after_replan",
    )
    assert resume_response.status_code == 200
    assert resume_response.json()["data"]["status"] == "active"
    _complete_project_via_governance_chain(client=client, project_id="project_m7_wp6_completed")

    readonly_payload = _build_project_chat_payload(
        project_id="project_m7_wp6_completed",
        action="msg_send",
        channel_id="channel-m7-wp6-project",
    )
    readonly_response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(readonly_payload),
        json=readonly_payload,
    )
    assert readonly_response.status_code == 403
    assert readonly_response.json()["error"]["code"] == "governance_project_channel_read_only"

    query_payload = _build_project_chat_payload(
        project_id="project_m7_wp6_completed",
        action="query_project_status",
        channel_id="channel-m7-wp6-project",
    )
    query_response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(query_payload),
        json=query_payload,
    )
    assert query_response.status_code == 202
    assert query_response.json()["status"] == "accepted"

    archive_response = _transition_project_lifecycle(
        client=client,
        project_id="project_m7_wp6_completed",
        action="archive",
        actor_id="ceo_m7_wp6",
        actor_role="ceo",
        trace_id="trace-m7-wp6-archive",
        reason_code="archive_after_completion",
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["data"]["status"] == "archived"

    archived_query_payload = _build_project_chat_payload(
        project_id="project_m7_wp6_completed",
        action="query_project_status",
        channel_id="channel-m7-wp6-project",
    )
    archived_query_response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(archived_query_payload),
        json=archived_query_payload,
    )
    assert archived_query_response.status_code == 403
    assert archived_query_response.json()["error"]["code"] == "governance_project_channel_archived"


def test_m7_wp6_acceptance_terminated_archive_branch_and_transition_guard(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("OPENQILIN_SYSTEM_ROOT", str(tmp_path / "openqilin-system"))
    client = TestClient(create_control_plane_app())

    _create_project(
        client=client,
        project_id="project_m7_wp6_terminated",
        name="M7 WP6 Terminated Path",
        objective="Validate terminated->archived acceptance branch",
    )
    _approve_project_by_triad(client=client, project_id="project_m7_wp6_terminated")
    _initialize_active_project(client=client, project_id="project_m7_wp6_terminated")

    terminate_response = _transition_project_lifecycle(
        client=client,
        project_id="project_m7_wp6_terminated",
        action="terminate",
        actor_id="cwo_m7_wp6",
        actor_role="cwo",
        trace_id="trace-m7-wp6-terminate",
        reason_code="terminated_by_cwo_decision",
    )
    assert terminate_response.status_code == 200
    assert terminate_response.json()["data"]["status"] == "terminated"

    archived_response = _transition_project_lifecycle(
        client=client,
        project_id="project_m7_wp6_terminated",
        action="archive",
        actor_id="ceo_m7_wp6",
        actor_role="ceo",
        trace_id="trace-m7-wp6-terminated-archive",
        reason_code="archive_after_termination",
    )
    assert archived_response.status_code == 200
    assert archived_response.json()["data"]["status"] == "archived"

    _create_project(
        client=client,
        project_id="project_m7_wp6_invalid_transition",
        name="M7 WP6 Invalid Transition Guard",
        objective="Validate completion->termination guard",
    )
    _approve_project_by_triad(client=client, project_id="project_m7_wp6_invalid_transition")
    _initialize_active_project(client=client, project_id="project_m7_wp6_invalid_transition")
    _complete_project_via_governance_chain(
        client=client, project_id="project_m7_wp6_invalid_transition"
    )
    invalid_transition_response = _transition_project_lifecycle(
        client=client,
        project_id="project_m7_wp6_invalid_transition",
        action="terminate",
        actor_id="ceo_m7_wp6",
        actor_role="ceo",
        trace_id="trace-m7-wp6-invalid-transition-attempt",
        reason_code="invalid_completed_to_terminated",
    )
    assert invalid_transition_response.status_code == 409
    assert invalid_transition_response.json()["error"]["code"] == "project_invalid_transition"
