from pathlib import Path

from fastapi.testclient import TestClient

from openqilin.apps.api_app import create_app
from openqilin.apps.orchestrator_worker import drain_queued_tasks
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def _query_headers(*, trace_id: str, actor_id: str, project_scope: str) -> dict[str, str]:
    return {
        "X-Trace-Id": trace_id,
        "X-External-Channel": "discord",
        "X-External-Actor-Id": actor_id,
        "X-OpenQilin-Project-Scope": project_scope,
    }


def test_m2_execution_targets_conformance_sandbox_and_llm_paths() -> None:
    app = create_app()
    client = TestClient(app)
    services = app.state.runtime_services

    sandbox_payload = build_owner_command_request_dict(
        action="run_task",
        args=["conformance"],
        actor_id="owner_m2_conformance_001",
        idempotency_key="idem-m2-conformance-sandbox",
        trace_id="trace-m2-conformance-sandbox",
    )
    sandbox_response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(sandbox_payload),
        json=sandbox_payload,
    )
    sandbox_body = sandbox_response.json()
    assert sandbox_response.status_code == 202
    assert sandbox_body["status"] == "accepted"
    sandbox_task_id = sandbox_body["data"]["task_id"]

    llm_payload = build_owner_command_request_dict(
        action="llm_summarize",
        args=["conformance"],
        actor_id="owner_m2_conformance_002",
        idempotency_key="idem-m2-conformance-llm",
        trace_id="trace-m2-conformance-llm",
    )
    llm_response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(llm_payload),
        json=llm_payload,
    )
    llm_body = llm_response.json()
    assert llm_response.status_code == 202
    assert llm_body["status"] == "accepted"
    llm_task_id = llm_body["data"]["task_id"]

    drain_queued_tasks(services)

    sandbox_task = client.get(f"/v1/tasks/{sandbox_task_id}").json()
    assert sandbox_task["status"] == "dispatched"
    assert sandbox_task["dispatch_target"] == "sandbox"
    assert sandbox_task["dispatch_id"]

    llm_task = client.get(f"/v1/tasks/{llm_task_id}").json()
    assert llm_task["status"] == "dispatched"
    assert llm_task["dispatch_target"] == "llm"
    assert llm_task["llm_execution"]["model_selected"]
    assert llm_task["llm_execution"]["usage"]["total_tokens"] > 0
    assert llm_task["llm_execution"]["cost"]["cost_source"] in {
        "pricing_table",
        "free_tier_assumed_zero",
        "none",
    }


def test_m2_execution_targets_conformance_retrieval_scope_and_fail_closed() -> None:
    client = TestClient(create_app())

    ok_response = client.post(
        "/v1/projects/project_1/artifacts/search",
        headers=_query_headers(
            trace_id="trace-m2-conformance-query-ok",
            actor_id="owner_m2_conformance_query_001",
            project_scope="project_1",
        ),
        json={"query": "execution targets", "limit": 5},
    )
    ok_body = ok_response.json()
    assert ok_response.status_code == 200
    assert ok_body["status"] == "ok"
    assert ok_body["data"]["project_id"] == "project_1"
    assert ok_body["data"]["result_count"] == len(ok_body["data"]["results"])

    deny_response = client.post(
        "/v1/projects/project_1/artifacts/search",
        headers=_query_headers(
            trace_id="trace-m2-conformance-query-deny",
            actor_id="owner_m2_conformance_query_001",
            project_scope="project_1",
        ),
        json={"query": "retrieval_error", "limit": 5},
    )
    deny_body = deny_response.json()
    assert deny_response.status_code == 403
    assert deny_body["status"] == "denied"
    assert deny_body["error"]["code"] == "retrieval_runtime_error_fail_closed"
    assert deny_body["error"]["source_component"] == "retrieval_runtime"


def test_m2_execution_targets_conformance_pgvector_contract_artifacts_present() -> None:
    project_root = Path(__file__).resolve().parents[2]
    migration_file = (
        project_root / "migrations" / "versions" / "20260311_0001_pgvector_baseline_contract.py"
    )
    migration_readme = project_root / "migrations" / "README.md"

    migration_content = migration_file.read_text(encoding="utf-8")
    readme_content = migration_readme.read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS vector" in migration_content
    assert "knowledge_embedding" in migration_content
    assert "embedding vector(1536)" in migration_content
    assert "20260311_0001_pgvector_baseline_contract.py" in readme_content
