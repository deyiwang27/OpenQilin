from __future__ import annotations

from pathlib import Path

from openqilin.data_access.repositories.artifacts import InMemoryProjectArtifactRepository
from openqilin.data_access.repositories.communication import InMemoryCommunicationRepository
from openqilin.data_access.repositories.governance import InMemoryGovernanceRepository
from openqilin.data_access.repositories.runtime_state import InMemoryRuntimeStateRepository
from openqilin.execution_sandbox.tools.contracts import ToolCallContext
from openqilin.execution_sandbox.tools.read_tools import GovernedReadToolService
from openqilin.observability.audit.audit_writer import InMemoryAuditWriter
from openqilin.retrieval_runtime.service import build_retrieval_query_service


def _build_context(
    *, role: str = "ceo", project_id: str | None = "project_alpha"
) -> ToolCallContext:
    return ToolCallContext(
        task_id="task-read-tools-001",
        request_id="request-read-tools-001",
        trace_id="trace-read-tools-001",
        principal_id="owner_001",
        recipient_role=role,
        recipient_id=f"{role}_core",
        project_id=project_id,
    )


def _build_service(tmp_path: Path) -> GovernedReadToolService:
    artifact_repository = InMemoryProjectArtifactRepository(system_root=tmp_path / "system_root")
    governance_repository = InMemoryGovernanceRepository(artifact_repository=artifact_repository)
    governance_repository.create_project(
        project_id="project_alpha",
        name="Project Alpha",
        objective="Deliver Alpha runtime.",
        status="proposed",
    )
    return GovernedReadToolService(
        governance_repository=governance_repository,
        project_artifact_repository=artifact_repository,
        runtime_state_repository=InMemoryRuntimeStateRepository(),
        retrieval_query_service=build_retrieval_query_service(),
        audit_writer=InMemoryAuditWriter(),
        communication_repository=InMemoryCommunicationRepository(),
    )


def test_read_tool_lifecycle_state_returns_citation_metadata(tmp_path: Path) -> None:
    service = _build_service(tmp_path)

    result = service.call_tool(
        tool_name="get_project_lifecycle_state",
        arguments={"project_id": "project_alpha"},
        context=_build_context(),
    )

    assert result.decision == "ok"
    assert result.data is not None
    assert result.data["status"] == "proposed"
    assert len(result.sources) == 1
    source = result.sources[0]
    assert source.source_id == "project:project_alpha"
    assert source.source_kind == "project_record"
    assert source.version == "status:proposed"
    assert source.updated_at is not None


def test_read_tool_denies_project_scope_mismatch_fail_closed(tmp_path: Path) -> None:
    service = _build_service(tmp_path)

    result = service.call_tool(
        tool_name="get_project_task_board",
        arguments={"project_id": "project_beta"},
        context=_build_context(project_id="project_alpha"),
    )

    assert result.decision == "denied"
    assert result.error_code == "tool_project_scope_mismatch"


def test_read_tool_denies_disallowed_role_access(tmp_path: Path) -> None:
    service = _build_service(tmp_path)

    result = service.call_tool(
        tool_name="get_audit_event_stream",
        arguments={"project_id": "project_alpha", "limit": 5},
        context=_build_context(role="project_manager"),
    )

    assert result.decision == "denied"
    assert result.error_code == "tool_access_denied"
