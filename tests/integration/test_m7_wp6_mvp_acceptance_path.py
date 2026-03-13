from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.data_access.repositories.governance import GovernanceRepositoryError
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def _governance_headers(*, actor_id: str, actor_role: str) -> dict[str, str]:
    return {
        "X-External-Channel": "discord",
        "X-External-Actor-Id": actor_id,
        "X-OpenQilin-Actor-Role": actor_role,
    }


def _approve_project_by_triad(*, client: TestClient, project_id: str) -> None:
    for actor_role in ("owner", "ceo", "cwo"):
        response = client.post(
            f"/v1/governance/projects/{project_id}/proposal/approve",
            headers=_governance_headers(actor_id=f"{actor_role}_m7_wp6", actor_role=actor_role),
            json={"trace_id": f"trace-m7-wp6-approve-{actor_role}-{project_id}"},
        )
        assert response.status_code == 200


def _create_project(*, client: TestClient, project_id: str, name: str, objective: str) -> None:
    response = client.post(
        "/v1/governance/projects",
        headers=_governance_headers(actor_id="owner_m7_wp6", actor_role="owner"),
        json={
            "trace_id": f"trace-m7-wp6-create-{project_id}",
            "project_id": project_id,
            "name": name,
            "objective": objective,
            "metadata": {"suite": "m7_wp6_acceptance"},
        },
    )
    assert response.status_code == 201


def _initialize_active_project(*, client: TestClient, project_id: str) -> dict[str, object]:
    response = client.post(
        f"/v1/governance/projects/{project_id}/initialize",
        headers=_governance_headers(actor_id="cwo_m7_wp6", actor_role="cwo"),
        json={
            "trace_id": f"trace-m7-wp6-init-{project_id}",
            "objective": "Deliver governed MVP acceptance scenario",
            "budget_currency_total": 100.0,
            "budget_quota_total": 1000.0,
            "metric_plan": {"delivery": "all_acceptance_checks_green"},
            "workforce_plan": {"project_manager": "1", "specialist": "2"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["status"] == "active"
    return body["data"]


def _bind_project_manager(*, client: TestClient, project_id: str) -> None:
    response = client.post(
        f"/v1/governance/projects/{project_id}/workforce/bind",
        headers=_governance_headers(actor_id="cwo_m7_wp6", actor_role="cwo"),
        json={
            "trace_id": f"trace-m7-wp6-bind-{project_id}",
            "role": "project_manager",
            "template_id": "project_manager_template_v1",
            "llm_routing_profile": "dev_gemini_free",
            "system_prompt": (
                "You are Project Manager. Mandatory operations: milestone planning, "
                "task decomposition, task assignment, progress reporting."
            ),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["binding_status"] == "active"


def _complete_project_via_governance_chain(*, client: TestClient, project_id: str) -> None:
    report = client.post(
        f"/v1/governance/projects/{project_id}/completion/report",
        headers=_governance_headers(actor_id="pm_m7_wp6", actor_role="project_manager"),
        json={
            "trace_id": f"trace-m7-wp6-completion-report-{project_id}",
            "summary": "All acceptance checks are complete.",
            "metric_results": {"mvp_acceptance": "passed"},
        },
    )
    assert report.status_code == 201
    cwo_approval = client.post(
        f"/v1/governance/projects/{project_id}/completion/approve",
        headers=_governance_headers(actor_id="cwo_m7_wp6", actor_role="cwo"),
        json={"trace_id": f"trace-m7-wp6-completion-approval-cwo-{project_id}"},
    )
    assert cwo_approval.status_code == 200
    ceo_approval = client.post(
        f"/v1/governance/projects/{project_id}/completion/approve",
        headers=_governance_headers(actor_id="ceo_m7_wp6", actor_role="ceo"),
        json={"trace_id": f"trace-m7-wp6-completion-approval-ceo-{project_id}"},
    )
    assert ceo_approval.status_code == 200
    finalize = client.post(
        f"/v1/governance/projects/{project_id}/completion/finalize",
        headers=_governance_headers(actor_id="cwo_m7_wp6", actor_role="cwo"),
        json={"trace_id": f"trace-m7-wp6-completion-finalize-{project_id}"},
    )
    assert finalize.status_code == 200
    assert finalize.json()["data"]["status"] == "completed"


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
    repo = app.state.runtime_services.governance_repo
    client = TestClient(app)
    _create_project(
        client=client,
        project_id="project_m7_wp6_completed",
        name="M7 WP6 Completed Path",
        objective="Validate completed->archived acceptance branch",
    )

    discussion = client.post(
        "/v1/governance/projects/project_m7_wp6_completed/proposal/messages",
        headers=_governance_headers(actor_id="owner_m7_wp6", actor_role="owner"),
        json={
            "trace_id": "trace-m7-wp6-discussion-completed",
            "content": "Propose MVP acceptance project and delivery criteria.",
        },
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

    repo.transition_project_status(
        project_id="project_m7_wp6_completed",
        next_status="paused",
        reason_code="pm_status_report_replan",
        actor_role="project_manager",
        trace_id="trace-m7-wp6-pause",
    )
    repo.transition_project_status(
        project_id="project_m7_wp6_completed",
        next_status="active",
        reason_code="pm_resume_after_replan",
        actor_role="project_manager",
        trace_id="trace-m7-wp6-resume",
    )
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

    archived_project = repo.transition_project_status(
        project_id="project_m7_wp6_completed",
        next_status="archived",
        reason_code="archive_after_completion",
        actor_role="ceo",
        trace_id="trace-m7-wp6-archive",
    )
    assert archived_project.status == "archived"

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
    app = create_control_plane_app()
    repo = app.state.runtime_services.governance_repo
    client = TestClient(app)

    _create_project(
        client=client,
        project_id="project_m7_wp6_terminated",
        name="M7 WP6 Terminated Path",
        objective="Validate terminated->archived acceptance branch",
    )
    _approve_project_by_triad(client=client, project_id="project_m7_wp6_terminated")
    _initialize_active_project(client=client, project_id="project_m7_wp6_terminated")

    terminated_project = repo.transition_project_status(
        project_id="project_m7_wp6_terminated",
        next_status="terminated",
        reason_code="terminated_by_cwo_decision",
        actor_role="cwo",
        trace_id="trace-m7-wp6-terminate",
    )
    assert terminated_project.status == "terminated"

    archived_project = repo.transition_project_status(
        project_id="project_m7_wp6_terminated",
        next_status="archived",
        reason_code="archive_after_termination",
        actor_role="ceo",
        trace_id="trace-m7-wp6-terminated-archive",
    )
    assert archived_project.status == "archived"

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
    with pytest.raises(GovernanceRepositoryError) as error:
        repo.transition_project_status(
            project_id="project_m7_wp6_invalid_transition",
            next_status="terminated",
            reason_code="invalid_completed_to_terminated",
            actor_role="ceo",
            trace_id="trace-m7-wp6-invalid-transition-attempt",
        )
    assert error.value.code == "project_invalid_transition"
