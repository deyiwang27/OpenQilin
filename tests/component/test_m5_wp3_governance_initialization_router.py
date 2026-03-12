from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app


def _headers(*, actor_id: str, actor_role: str) -> dict[str, str]:
    return {
        "X-External-Channel": "discord",
        "X-External-Actor-Id": actor_id,
        "X-OpenQilin-Actor-Role": actor_role,
    }


def _seed_approved_project() -> TestClient:
    app = create_control_plane_app()
    repository = app.state.runtime_services.governance_repo
    repository.create_project(
        project_id="project_m5_wp3",
        name="M5 Initialization Router",
        objective="Seed objective",
    )
    repository.transition_project_status(
        project_id="project_m5_wp3",
        next_status="approved",
        reason_code="triad_approval",
        actor_role="ceo",
        trace_id="trace-m5-wp3-seed-approval",
    )
    return TestClient(app)


def test_initialize_project_accepts_cwo_and_activates_project() -> None:
    client = _seed_approved_project()

    response = client.post(
        "/v1/governance/projects/project_m5_wp3/initialize",
        headers=_headers(actor_id="cwo_1", actor_role="cwo"),
        json={
            "trace_id": "trace-m5-wp3-init-router",
            "objective": "Initialize MVP governance project",
            "budget_currency_total": 250.0,
            "budget_quota_total": 10000.0,
            "metric_plan": {"completion": "all_wp_passed"},
            "workforce_plan": {"pm": "1", "specialist": "2"},
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["project_id"] == "project_m5_wp3"
    assert body["data"]["status"] == "active"
    assert body["data"]["objective"] == "Initialize MVP governance project"
    assert body["data"]["budget_currency_total"] == 250.0
    assert body["data"]["budget_quota_total"] == 10000.0


def test_initialize_project_rejects_non_cwo_role() -> None:
    client = _seed_approved_project()

    response = client.post(
        "/v1/governance/projects/project_m5_wp3/initialize",
        headers=_headers(actor_id="owner_1", actor_role="owner"),
        json={
            "trace_id": "trace-m5-wp3-init-router-denied-role",
            "objective": "Should fail",
            "budget_currency_total": 1.0,
            "budget_quota_total": 1.0,
            "metric_plan": {},
            "workforce_plan": {},
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_role_forbidden"


def test_initialize_project_rejects_not_approved_status() -> None:
    app = create_control_plane_app()
    app.state.runtime_services.governance_repo.create_project(
        project_id="project_m5_wp3",
        name="M5 Initialization Router",
        objective="Seed objective",
    )
    client = TestClient(app)

    response = client.post(
        "/v1/governance/projects/project_m5_wp3/initialize",
        headers=_headers(actor_id="cwo_1", actor_role="cwo"),
        json={
            "trace_id": "trace-m5-wp3-init-router-not-approved",
            "objective": "Should fail",
            "budget_currency_total": 1.0,
            "budget_quota_total": 1.0,
            "metric_plan": {},
            "workforce_plan": {},
        },
    )

    body = response.json()
    assert response.status_code == 409
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_project_not_approved"
