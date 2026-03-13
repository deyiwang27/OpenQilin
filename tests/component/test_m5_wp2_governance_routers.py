from fastapi.testclient import TestClient
from typing import Mapping

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


def _seed_project(app_project_id: str = "project_m5_wp2") -> TestClient:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = {
        "trace_id": f"trace-m5-wp2-create-{app_project_id}",
        "project_id": app_project_id,
        "name": "M5 Governance APIs",
        "objective": "Validate proposal discussion and approval routes.",
        "metadata": {"suite": "component"},
    }
    response = _post_governance(
        client=client,
        path="/v1/governance/projects",
        actor_id="owner_1",
        actor_role="owner",
        payload=payload,
    )
    assert response.status_code == 201
    return client


def test_create_project_accepts_owner_and_sets_proposed_status() -> None:
    app = create_control_plane_app()
    client = TestClient(app)

    payload = {
        "trace_id": "trace-m5-wp2-create",
        "project_id": "project_m5_wp2_create",
        "name": "M5 Governance APIs",
        "objective": "Validate project creation route.",
        "metadata": {"suite": "component"},
    }
    response = _post_governance(
        client=client,
        path="/v1/governance/projects",
        actor_id="owner_1",
        actor_role="owner",
        payload=payload,
    )

    body = response.json()
    assert response.status_code == 201
    assert body["status"] == "ok"
    assert body["data"]["project_id"] == "project_m5_wp2_create"
    assert body["data"]["status"] == "proposed"


def test_create_project_rejects_non_triad_role() -> None:
    app = create_control_plane_app()
    client = TestClient(app)

    payload = {
        "trace_id": "trace-m5-wp2-create-denied",
        "project_id": "project_m5_wp2_create_denied",
        "name": "M5 Governance APIs",
        "objective": "Validate project creation route.",
        "metadata": {"suite": "component"},
    }
    response = _post_governance(
        client=client,
        path="/v1/governance/projects",
        actor_id="admin_1",
        actor_role="administrator",
        payload=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_project_create_role_forbidden"


def test_create_project_rejects_missing_signature_header() -> None:
    client = TestClient(create_control_plane_app())
    payload = {
        "trace_id": "trace-m8-wp1-create-missing-signature",
        "project_id": "project_m8_wp1_missing_signature",
        "name": "M8 Governance APIs",
        "objective": "Validate connector signature requirement.",
        "metadata": {"suite": "component"},
    }
    headers = build_governance_headers(
        payload=payload,
        actor_id="owner_1",
        actor_role="owner",
    )
    headers.pop("X-OpenQilin-Signature")

    response = client.post(
        "/v1/governance/projects",
        headers=headers,
        json=payload,
    )

    body = response.json()
    assert response.status_code == 400
    assert body["status"] == "error"
    assert body["error"]["code"] == "connector_signature_missing"


def test_post_proposal_discussion_message_accepts_owner() -> None:
    client = _seed_project()

    payload = {
        "trace_id": "trace-m5-wp2-message",
        "content": "Proposal discussion message from owner.",
    }
    response = _post_governance(
        client=client,
        path="/v1/governance/projects/project_m5_wp2/proposal/messages",
        actor_id="owner_1",
        actor_role="owner",
        payload=payload,
    )

    body = response.json()
    assert response.status_code == 201
    assert body["status"] == "ok"
    assert body["trace_id"] == "trace-m5-wp2-message"
    assert body["data"]["project_id"] == "project_m5_wp2"
    assert body["data"]["status"] == "proposed"
    assert body["data"]["actor_role"] == "owner"


def test_post_proposal_discussion_message_rejects_connector_actor_mismatch() -> None:
    client = _seed_project()
    payload = {
        "trace_id": "trace-m8-wp1-discussion-actor-mismatch",
        "content": "Connector headers should enforce actor parity.",
    }
    headers = build_governance_headers(
        payload=payload,
        actor_id="owner_1",
        actor_role="owner",
    )
    headers["X-OpenQilin-Actor-External-Id"] = "owner_mismatch"

    response = client.post(
        "/v1/governance/projects/project_m5_wp2/proposal/messages",
        headers=headers,
        json=payload,
    )

    body = response.json()
    assert response.status_code == 400
    assert body["status"] == "error"
    assert body["error"]["code"] == "connector_actor_mismatch"


def test_post_proposal_discussion_message_rejects_non_triad_role() -> None:
    client = _seed_project()

    payload = {
        "trace_id": "trace-m5-wp2-message-denied",
        "content": "Auditor should not be allowed in proposal discussion.",
    }
    response = _post_governance(
        client=client,
        path="/v1/governance/projects/project_m5_wp2/proposal/messages",
        actor_id="auditor_1",
        actor_role="auditor",
        payload=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_role_forbidden"


def test_proposal_approval_promotes_project_after_triad_approvals() -> None:
    client = _seed_project()

    owner_payload = {"trace_id": "trace-m5-wp2-owner-approval"}
    owner_response = _post_governance(
        client=client,
        path="/v1/governance/projects/project_m5_wp2/proposal/approve",
        actor_id="owner_1",
        actor_role="owner",
        payload=owner_payload,
    )
    ceo_payload = {"trace_id": "trace-m5-wp2-ceo-approval"}
    ceo_response = _post_governance(
        client=client,
        path="/v1/governance/projects/project_m5_wp2/proposal/approve",
        actor_id="ceo_1",
        actor_role="ceo",
        payload=ceo_payload,
    )
    cwo_payload = {"trace_id": "trace-m5-wp2-cwo-approval"}
    cwo_response = _post_governance(
        client=client,
        path="/v1/governance/projects/project_m5_wp2/proposal/approve",
        actor_id="cwo_1",
        actor_role="cwo",
        payload=cwo_payload,
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

    payload = {"trace_id": "trace-m5-wp2-admin-approval"}
    response = _post_governance(
        client=client,
        path="/v1/governance/projects/project_m5_wp2/proposal/approve",
        actor_id="admin_1",
        actor_role="administrator",
        payload=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_approval_role_forbidden"
