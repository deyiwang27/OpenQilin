from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app


def _headers(*, actor_id: str, actor_role: str) -> dict[str, str]:
    return {
        "X-External-Channel": "discord",
        "X-External-Actor-Id": actor_id,
        "X-OpenQilin-Actor-Role": actor_role,
    }


def _seed_active_project() -> TestClient:
    app = create_control_plane_app()
    repository = app.state.runtime_services.governance_repo
    repository.create_project(
        project_id="project_m5_wp4",
        name="M5 Workforce Binding Router",
        objective="Seed objective",
    )
    repository.transition_project_status(
        project_id="project_m5_wp4",
        next_status="approved",
        reason_code="triad_approval",
        actor_role="ceo",
        trace_id="trace-m5-wp4-seed-approval",
    )
    repository.initialize_project(
        project_id="project_m5_wp4",
        objective="Initialized objective",
        budget_currency_total=100.0,
        budget_quota_total=1000.0,
        metric_plan={"delivery": "ok"},
        workforce_plan={"project_manager": "1"},
        actor_id="cwo_1",
        actor_role="cwo",
        trace_id="trace-m5-wp4-seed-init",
    )
    return TestClient(app)


def test_bind_project_manager_template_as_cwo_returns_active_binding() -> None:
    client = _seed_active_project()

    response = client.post(
        "/v1/governance/projects/project_m5_wp4/workforce/bind",
        headers=_headers(actor_id="cwo_1", actor_role="cwo"),
        json={
            "trace_id": "trace-m5-wp4-bind-project-manager",
            "role": "project_manager",
            "template_id": "project_manager_template_v1",
            "llm_routing_profile": "dev_gemini_free",
            "system_prompt": "You are Project Manager.",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["role"] == "project_manager"
    assert body["data"]["binding_status"] == "active"
    assert len(body["data"]["system_prompt_hash"]) == 64


def test_bind_domain_leader_template_stays_declared_disabled() -> None:
    client = _seed_active_project()

    response = client.post(
        "/v1/governance/projects/project_m5_wp4/workforce/bind",
        headers=_headers(actor_id="cwo_1", actor_role="cwo"),
        json={
            "trace_id": "trace-m5-wp4-bind-dl",
            "role": "domain_leader",
            "template_id": "domain_leader_template_v1",
            "llm_routing_profile": "dev_gemini_free",
            "system_prompt": "You are Domain Leader.",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["role"] == "domain_leader"
    assert body["data"]["binding_status"] == "declared_disabled"


def test_bind_workforce_template_rejects_non_cwo_role() -> None:
    client = _seed_active_project()

    response = client.post(
        "/v1/governance/projects/project_m5_wp4/workforce/bind",
        headers=_headers(actor_id="owner_1", actor_role="owner"),
        json={
            "trace_id": "trace-m5-wp4-bind-denied",
            "role": "project_manager",
            "template_id": "project_manager_template_v1",
            "llm_routing_profile": "dev_gemini_free",
            "system_prompt": "You are Project Manager.",
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_role_forbidden"
