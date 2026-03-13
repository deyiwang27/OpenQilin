from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app


def _headers(*, actor_id: str, actor_role: str) -> dict[str, str]:
    return {
        "X-External-Channel": "discord",
        "X-External-Actor-Id": actor_id,
        "X-OpenQilin-Actor-Role": actor_role,
    }


def _seed_active_project(client: TestClient, project_id: str) -> None:
    create = client.post(
        "/v1/governance/projects",
        headers=_headers(actor_id="owner_1", actor_role="owner"),
        json={
            "trace_id": f"trace-{project_id}-create",
            "project_id": project_id,
            "name": "Completion Governance Project",
            "objective": "Validate completion governance chain",
            "metadata": {},
        },
    )
    assert create.status_code == 201
    for role in ("owner", "ceo", "cwo"):
        approval = client.post(
            f"/v1/governance/projects/{project_id}/proposal/approve",
            headers=_headers(actor_id=f"{role}_1", actor_role=role),
            json={"trace_id": f"trace-{project_id}-approve-{role}"},
        )
        assert approval.status_code == 200
    initialize = client.post(
        f"/v1/governance/projects/{project_id}/initialize",
        headers=_headers(actor_id="cwo_1", actor_role="cwo"),
        json={
            "trace_id": f"trace-{project_id}-initialize",
            "objective": "Run completion chain",
            "budget_currency_total": 100.0,
            "budget_quota_total": 1000.0,
            "metric_plan": {"delivery": "green"},
            "workforce_plan": {"project_manager": "1"},
        },
    )
    assert initialize.status_code == 200


def test_completion_governance_chain_allows_finalization_after_report_and_co_approval() -> None:
    client = TestClient(create_control_plane_app())
    project_id = "project_m7_completion_success"
    _seed_active_project(client, project_id)

    report = client.post(
        f"/v1/governance/projects/{project_id}/completion/report",
        headers=_headers(actor_id="pm_1", actor_role="project_manager"),
        json={
            "trace_id": f"trace-{project_id}-report",
            "summary": "Project delivered all scoped objectives.",
            "metric_results": {"quality_gate": "passed"},
        },
    )
    assert report.status_code == 201
    assert report.json()["data"]["completion_report_storage_uri"] is not None

    cwo_approval = client.post(
        f"/v1/governance/projects/{project_id}/completion/approve",
        headers=_headers(actor_id="cwo_1", actor_role="cwo"),
        json={"trace_id": f"trace-{project_id}-approval-cwo"},
    )
    assert cwo_approval.status_code == 200
    assert cwo_approval.json()["data"]["owner_notified"] is False

    ceo_approval = client.post(
        f"/v1/governance/projects/{project_id}/completion/approve",
        headers=_headers(actor_id="ceo_1", actor_role="ceo"),
        json={"trace_id": f"trace-{project_id}-approval-ceo"},
    )
    assert ceo_approval.status_code == 200
    assert ceo_approval.json()["data"]["owner_notified"] is True

    finalize = client.post(
        f"/v1/governance/projects/{project_id}/completion/finalize",
        headers=_headers(actor_id="cwo_1", actor_role="cwo"),
        json={"trace_id": f"trace-{project_id}-finalize"},
    )
    body = finalize.json()
    assert finalize.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["status"] == "completed"


def test_completion_finalize_denies_when_report_and_approval_chain_missing() -> None:
    client = TestClient(create_control_plane_app())
    project_id = "project_m7_completion_missing_chain"
    _seed_active_project(client, project_id)

    finalize = client.post(
        f"/v1/governance/projects/{project_id}/completion/finalize",
        headers=_headers(actor_id="ceo_1", actor_role="ceo"),
        json={"trace_id": f"trace-{project_id}-finalize"},
    )

    body = finalize.json()
    assert finalize.status_code == 409
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_project_completion_report_missing"


def test_completion_report_denies_non_project_manager_actor() -> None:
    client = TestClient(create_control_plane_app())
    project_id = "project_m7_completion_report_denied"
    _seed_active_project(client, project_id)

    report = client.post(
        f"/v1/governance/projects/{project_id}/completion/report",
        headers=_headers(actor_id="owner_1", actor_role="owner"),
        json={
            "trace_id": f"trace-{project_id}-report-denied",
            "summary": "Should fail because actor role is owner.",
            "metric_results": {},
        },
    )

    body = report.json()
    assert report.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_project_completion_report_role_forbidden"
