from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app


def _governance_headers(*, actor_id: str, actor_role: str) -> dict[str, str]:
    return {
        "X-External-Channel": "discord",
        "X-External-Actor-Id": actor_id,
        "X-OpenQilin-Actor-Role": actor_role,
    }


def _seed_project(app_project_id: str = "project_m5_wp2") -> TestClient:
    app = create_control_plane_app()
    client = TestClient(app)
    response = client.post(
        "/v1/governance/projects",
        headers=_governance_headers(actor_id="owner_1", actor_role="owner"),
        json={
            "trace_id": f"trace-m5-wp2-create-{app_project_id}",
            "project_id": app_project_id,
            "name": "M5 Governance APIs",
            "objective": "Validate proposal discussion and approval routes.",
            "metadata": {"suite": "component"},
        },
    )
    assert response.status_code == 201
    return client


def test_create_project_accepts_owner_and_sets_proposed_status() -> None:
    app = create_control_plane_app()
    client = TestClient(app)

    response = client.post(
        "/v1/governance/projects",
        headers=_governance_headers(actor_id="owner_1", actor_role="owner"),
        json={
            "trace_id": "trace-m5-wp2-create",
            "project_id": "project_m5_wp2_create",
            "name": "M5 Governance APIs",
            "objective": "Validate project creation route.",
            "metadata": {"suite": "component"},
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["status"] == "ok"
    assert body["data"]["project_id"] == "project_m5_wp2_create"
    assert body["data"]["status"] == "proposed"


def test_create_project_rejects_non_triad_role() -> None:
    app = create_control_plane_app()
    client = TestClient(app)

    response = client.post(
        "/v1/governance/projects",
        headers=_governance_headers(actor_id="admin_1", actor_role="administrator"),
        json={
            "trace_id": "trace-m5-wp2-create-denied",
            "project_id": "project_m5_wp2_create_denied",
            "name": "M5 Governance APIs",
            "objective": "Validate project creation route.",
            "metadata": {"suite": "component"},
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_project_create_role_forbidden"


def test_post_proposal_discussion_message_accepts_owner() -> None:
    client = _seed_project()

    response = client.post(
        "/v1/governance/projects/project_m5_wp2/proposal/messages",
        headers=_governance_headers(actor_id="owner_1", actor_role="owner"),
        json={
            "trace_id": "trace-m5-wp2-message",
            "content": "Proposal discussion message from owner.",
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["status"] == "ok"
    assert body["trace_id"] == "trace-m5-wp2-message"
    assert body["data"]["project_id"] == "project_m5_wp2"
    assert body["data"]["status"] == "proposed"
    assert body["data"]["actor_role"] == "owner"


def test_post_proposal_discussion_message_rejects_non_triad_role() -> None:
    client = _seed_project()

    response = client.post(
        "/v1/governance/projects/project_m5_wp2/proposal/messages",
        headers=_governance_headers(actor_id="auditor_1", actor_role="auditor"),
        json={
            "trace_id": "trace-m5-wp2-message-denied",
            "content": "Auditor should not be allowed in proposal discussion.",
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_role_forbidden"


def test_proposal_approval_promotes_project_after_triad_approvals() -> None:
    client = _seed_project()

    owner_response = client.post(
        "/v1/governance/projects/project_m5_wp2/proposal/approve",
        headers=_governance_headers(actor_id="owner_1", actor_role="owner"),
        json={"trace_id": "trace-m5-wp2-owner-approval"},
    )
    ceo_response = client.post(
        "/v1/governance/projects/project_m5_wp2/proposal/approve",
        headers=_governance_headers(actor_id="ceo_1", actor_role="ceo"),
        json={"trace_id": "trace-m5-wp2-ceo-approval"},
    )
    cwo_response = client.post(
        "/v1/governance/projects/project_m5_wp2/proposal/approve",
        headers=_governance_headers(actor_id="cwo_1", actor_role="cwo"),
        json={"trace_id": "trace-m5-wp2-cwo-approval"},
    )

    assert owner_response.status_code == 200
    assert owner_response.json()["data"]["status"] == "proposed"
    assert ceo_response.status_code == 200
    assert ceo_response.json()["data"]["status"] == "proposed"
    assert cwo_response.status_code == 200
    body = cwo_response.json()
    assert body["status"] == "ok"
    assert body["data"]["status"] == "approved"
    assert set(body["data"]["approval_roles"]) == {"owner", "ceo", "cwo"}


def test_proposal_approval_rejects_role_outside_triad() -> None:
    client = _seed_project()

    response = client.post(
        "/v1/governance/projects/project_m5_wp2/proposal/approve",
        headers=_governance_headers(actor_id="admin_1", actor_role="administrator"),
        json={"trace_id": "trace-m5-wp2-admin-approval"},
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_approval_role_forbidden"
