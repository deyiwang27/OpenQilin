from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.data_access.repositories.artifacts import (
    InMemoryProjectArtifactRepository,
    ProjectDocumentPolicy,
)
from openqilin.data_access.repositories.governance import InMemoryGovernanceRepository


def _headers(*, actor_id: str, actor_role: str) -> dict[str, str]:
    return {
        "X-External-Channel": "discord",
        "X-External-Actor-Id": actor_id,
        "X-OpenQilin-Actor-Role": actor_role,
    }


def test_initialize_project_returns_governed_denial_for_artifact_policy_violation() -> None:
    app = create_control_plane_app()
    services = app.state.runtime_services
    policy_repo = InMemoryProjectArtifactRepository(
        policy=ProjectDocumentPolicy(
            allowed_type_caps={"project_charter": 1, "success_metrics": 1},
            total_active_document_cap=20,
        )
    )
    services.governance_repo = InMemoryGovernanceRepository(artifact_repository=policy_repo)
    services.governance_repo.create_project(
        project_id="project_m6_wp2",
        name="M6 Policy Router",
        objective="Seed objective",
    )
    services.governance_repo.transition_project_status(
        project_id="project_m6_wp2",
        next_status="approved",
        reason_code="triad_approval",
        actor_role="ceo",
        trace_id="trace-m6-wp2-seed-approval",
    )
    client = TestClient(app)

    response = client.post(
        "/v1/governance/projects/project_m6_wp2/initialize",
        headers=_headers(actor_id="cwo_1", actor_role="cwo"),
        json={
            "trace_id": "trace-m6-wp2-init-router",
            "objective": "Initialize MVP governance project",
            "budget_currency_total": 250.0,
            "budget_quota_total": 10000.0,
            "metric_plan": {"completion": "all_wp_passed"},
            "workforce_plan": {"project_manager": "1"},
        },
    )

    body = response.json()
    assert response.status_code == 409
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_project_artifact_policy_denied"
