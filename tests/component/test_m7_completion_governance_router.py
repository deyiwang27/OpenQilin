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


def _seed_active_project(client: TestClient, project_id: str) -> None:
    create_payload = {
        "trace_id": f"trace-{project_id}-create",
        "project_id": project_id,
        "name": "Completion Governance Project",
        "objective": "Validate completion governance chain",
        "metadata": {},
    }
    create = _post_governance(
        client=client,
        path="/v1/governance/projects",
        actor_id="owner_1",
        actor_role="owner",
        payload=create_payload,
    )
    assert create.status_code == 201
    for role in ("owner", "ceo", "cwo"):
        approval_payload = {"trace_id": f"trace-{project_id}-approve-{role}"}
        approval = _post_governance(
            client=client,
            path=f"/v1/governance/projects/{project_id}/proposal/approve",
            actor_id=f"{role}_1",
            actor_role=role,
            payload=approval_payload,
        )
        assert approval.status_code == 200
    initialize_payload = {
        "trace_id": f"trace-{project_id}-initialize",
        "objective": "Run completion chain",
        "budget_currency_total": 100.0,
        "budget_quota_total": 1000.0,
        "metric_plan": {"delivery": "green"},
        "workforce_plan": {"project_manager": "1"},
    }
    initialize = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/initialize",
        actor_id="cwo_1",
        actor_role="cwo",
        payload=initialize_payload,
    )
    assert initialize.status_code == 200


def test_completion_governance_chain_allows_finalization_after_report_and_co_approval() -> None:
    client = TestClient(create_control_plane_app())
    project_id = "project_m7_completion_success"
    _seed_active_project(client, project_id)

    report_payload = {
        "trace_id": f"trace-{project_id}-report",
        "summary": "Project delivered all scoped objectives.",
        "metric_results": {"quality_gate": "passed"},
    }
    report = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/completion/report",
        actor_id="pm_1",
        actor_role="project_manager",
        payload=report_payload,
    )
    assert report.status_code == 201
    assert report.json()["data"]["completion_report_storage_uri"] is not None

    cwo_approval_payload = {"trace_id": f"trace-{project_id}-approval-cwo"}
    cwo_approval = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/completion/approve",
        actor_id="cwo_1",
        actor_role="cwo",
        payload=cwo_approval_payload,
    )
    assert cwo_approval.status_code == 200
    assert cwo_approval.json()["data"]["owner_notified"] is False

    ceo_approval_payload = {"trace_id": f"trace-{project_id}-approval-ceo"}
    ceo_approval = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/completion/approve",
        actor_id="ceo_1",
        actor_role="ceo",
        payload=ceo_approval_payload,
    )
    assert ceo_approval.status_code == 200
    assert ceo_approval.json()["data"]["owner_notified"] is True

    finalize_payload = {"trace_id": f"trace-{project_id}-finalize"}
    finalize = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/completion/finalize",
        actor_id="cwo_1",
        actor_role="cwo",
        payload=finalize_payload,
    )
    body = finalize.json()
    assert finalize.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["status"] == "completed"


def test_completion_finalize_denies_when_report_and_approval_chain_missing() -> None:
    client = TestClient(create_control_plane_app())
    project_id = "project_m7_completion_missing_chain"
    _seed_active_project(client, project_id)

    finalize_payload = {"trace_id": f"trace-{project_id}-finalize"}
    finalize = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/completion/finalize",
        actor_id="ceo_1",
        actor_role="ceo",
        payload=finalize_payload,
    )

    body = finalize.json()
    assert finalize.status_code == 409
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_project_completion_report_missing"


def test_completion_report_denies_non_project_manager_actor() -> None:
    client = TestClient(create_control_plane_app())
    project_id = "project_m7_completion_report_denied"
    _seed_active_project(client, project_id)

    report_payload = {
        "trace_id": f"trace-{project_id}-report-denied",
        "summary": "Should fail because actor role is owner.",
        "metric_results": {},
    }
    report = _post_governance(
        client=client,
        path=f"/v1/governance/projects/{project_id}/completion/report",
        actor_id="owner_1",
        actor_role="owner",
        payload=report_payload,
    )

    body = report.json()
    assert report.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_project_completion_report_role_forbidden"
