from fastapi.testclient import TestClient

from openqilin.apps.api_app import app


def test_governed_ingress_generates_trace_id_when_header_missing() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_987",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "run_task",
            "args": ["alpha"],
            "idempotency_key": "idem-abcdefgh",
        },
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["principal_id"] == "owner_987"
    assert body["trace_id"]
    assert isinstance(body["trace_id"], str)
