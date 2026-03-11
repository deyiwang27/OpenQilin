from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app


def test_submit_owner_command_accepts_valid_payload() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_123",
            "X-OpenQilin-Connector": "discord",
            "X-OpenQilin-Trace-Id": "trace-component-1",
        },
        json={
            "command": "run_task",
            "args": ["alpha", "beta"],
            "idempotency_key": "idem-12345678",
        },
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["principal_id"] == "owner_123"
    assert body["trace_id"] == "trace-component-1"
    assert body["command"] == "run_task"
    assert body["accepted_args"] == ["alpha", "beta"]


def test_submit_owner_command_blocks_missing_principal_header() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-Connector": "discord",
            "X-OpenQilin-Trace-Id": "trace-component-2",
        },
        json={
            "command": "run_task",
            "args": ["alpha"],
            "idempotency_key": "idem-12345678",
        },
    )

    body = response.json()
    assert response.status_code == 400
    assert body["status"] == "blocked"
    assert body["error_code"] == "principal_missing_header"
    assert body["details"]["source"] == "headers"


def test_submit_owner_command_blocks_blank_command() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_123",
            "X-OpenQilin-Connector": "discord",
            "X-OpenQilin-Trace-Id": "trace-component-3",
        },
        json={
            "command": "   ",
            "args": ["alpha"],
            "idempotency_key": "idem-12345678",
        },
    )

    body = response.json()
    assert response.status_code == 400
    assert body["status"] == "blocked"
    assert body["error_code"] == "envelope_invalid_command"
    assert body["details"]["source"] == "payload"
