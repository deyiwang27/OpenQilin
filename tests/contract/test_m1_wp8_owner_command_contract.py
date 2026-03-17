from fastapi.testclient import TestClient

from openqilin.apps.orchestrator_worker import drain_queued_tasks
from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def test_owner_command_accepted_response_contract() -> None:
    app = create_control_plane_app()
    services = app.state.runtime_services
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="run_task",
        args=["alpha"],
        actor_id="owner_contract_accept",
        idempotency_key="idem-contract-accept-12345",
        trace_id="trace-contract-accept",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 202
    assert set(body.keys()) == {
        "status",
        "trace_id",
        "policy_version",
        "policy_hash",
        "rule_ids",
        "data",
        "error",
    }
    assert body["status"] == "accepted"
    assert body["trace_id"] == "trace-contract-accept"
    assert body["error"] is None

    data = body["data"]
    assert isinstance(data["task_id"], str) and data["task_id"]
    assert isinstance(data["replayed"], bool)
    assert data["principal_id"] == "owner_contract_accept"
    assert data["admission_state"] == "queued"

    task_id = data["task_id"]
    drain_queued_tasks(services)

    task_response = client.get(f"/v1/tasks/{task_id}")
    task_body = task_response.json()
    assert task_response.status_code == 200
    assert set(task_body.keys()) == {
        "task_id",
        "trace_id",
        "status",
        "principal_id",
        "principal_role",
        "command",
        "dispatch_target",
        "dispatch_id",
        "error_code",
        "error_message",
        "outcome_source",
        "policy_version",
        "policy_hash",
        "rule_ids",
        "llm_execution",
    }
    assert task_body["task_id"] == task_id
    assert task_body["status"] == "dispatched"
    assert isinstance(task_body["dispatch_id"], str) and task_body["dispatch_id"]
    assert task_body["error_code"] is None


def test_owner_command_denied_response_contract() -> None:
    app = create_control_plane_app()
    services = app.state.runtime_services
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="policy_uncertain",
        args=["alpha"],
        actor_id="owner_contract_block",
        idempotency_key="idem-contract-block-12345",
        trace_id="trace-contract-block",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["data"]["admission_state"] == "queued"

    task_id = body["data"]["task_id"]
    drain_queued_tasks(services)

    task_response = client.get(f"/v1/tasks/{task_id}")
    task_body = task_response.json()
    assert task_response.status_code == 200
    assert set(task_body.keys()) == {
        "task_id",
        "trace_id",
        "status",
        "principal_id",
        "principal_role",
        "command",
        "dispatch_target",
        "dispatch_id",
        "error_code",
        "error_message",
        "outcome_source",
        "policy_version",
        "policy_hash",
        "rule_ids",
        "llm_execution",
    }
    assert task_body["status"] == "blocked"
    assert task_body["error_code"] == "policy_uncertain_fail_closed"
    assert isinstance(task_body["error_message"], str) and task_body["error_message"]
    assert task_body["outcome_source"] == "policy_runtime"
    assert isinstance(task_body["policy_version"], str)
    assert isinstance(task_body["policy_hash"], str)
    assert isinstance(task_body["rule_ids"], list)


def test_owner_command_specialist_touchability_denied_response_contract() -> None:
    app = create_control_plane_app()
    services = app.state.runtime_services
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=["deliver update"],
        actor_id="owner_contract_specialist_block",
        idempotency_key="idem-contract-specialist-block-12345",
        trace_id="trace-contract-specialist-block",
        target="communication",
        recipients=[{"recipient_id": "specialist_1", "recipient_type": "specialist"}],
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"

    task_id = body["data"]["task_id"]
    drain_queued_tasks(services)

    task_response = client.get(f"/v1/tasks/{task_id}")
    task_body = task_response.json()
    assert task_response.status_code == 200
    assert task_body["status"] == "blocked"
    assert task_body["error_code"] == "governance_specialist_direct_command_denied"
    assert task_body["outcome_source"] == "policy_runtime"
