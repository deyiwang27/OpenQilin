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

    payload = {
        "trace_id": "trace-m5-wp4-bind-project-manager",
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
        path="/v1/governance/projects/project_m5_wp4/workforce/bind",
        actor_id="cwo_1",
        actor_role="cwo",
        payload=payload,
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["role"] == "project_manager"
    assert body["data"]["binding_status"] == "active"
    assert len(body["data"]["system_prompt_hash"]) == 64
    assert body["data"]["mandatory_operations"] == [
        "milestone_planning",
        "progress_reporting",
        "task_assignment",
        "task_decomposition",
    ]


def test_bind_domain_leader_template_stays_declared_disabled() -> None:
    client = _seed_active_project()

    payload = {
        "trace_id": "trace-m5-wp4-bind-dl",
        "role": "domain_leader",
        "template_id": "domain_leader_template_v1",
        "llm_routing_profile": "dev_gemini_free",
        "system_prompt": "You are Domain Leader.",
    }
    response = _post_governance(
        client=client,
        path="/v1/governance/projects/project_m5_wp4/workforce/bind",
        actor_id="cwo_1",
        actor_role="cwo",
        payload=payload,
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["role"] == "domain_leader"
    assert body["data"]["binding_status"] == "declared_disabled"


def test_bind_workforce_template_rejects_non_cwo_role() -> None:
    client = _seed_active_project()

    payload = {
        "trace_id": "trace-m5-wp4-bind-denied",
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
        path="/v1/governance/projects/project_m5_wp4/workforce/bind",
        actor_id="owner_1",
        actor_role="owner",
        payload=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_role_forbidden"


def test_bind_project_manager_template_rejects_missing_mandatory_operations() -> None:
    client = _seed_active_project()

    payload = {
        "trace_id": "trace-m6-wp4-bind-missing-ops-router",
        "role": "project_manager",
        "template_id": "project_manager_template_v1",
        "llm_routing_profile": "dev_gemini_free",
        "system_prompt": "You are Project Manager.",
    }
    response = _post_governance(
        client=client,
        path="/v1/governance/projects/project_m5_wp4/workforce/bind",
        actor_id="cwo_1",
        actor_role="cwo",
        payload=payload,
    )

    body = response.json()
    assert response.status_code == 409
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_project_manager_template_missing_operations"
