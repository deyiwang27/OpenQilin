"""M14-WP5 — Administrator Agent unit tests."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from openqilin.agents.administrator.agent import AdministratorAgent
from openqilin.agents.administrator.document_policy import DocumentPolicyEnforcer
from openqilin.agents.administrator.models import AdministratorRequest
from openqilin.agents.administrator.retention import RetentionEnforcer
from openqilin.data_access.repositories.agent_registry import (
    AgentRecord,
    AgentRegistryRepositoryError,
)
from openqilin.data_access.repositories.artifacts import ProjectArtifactWriteContext
from openqilin.observability.testing.stubs import InMemoryAuditWriter
from tests.testing.infra_stubs import InMemoryProjectArtifactRepository


@dataclass
class _StubAgentRegistryRepo:
    agents: dict[str, AgentRecord]

    def quarantine_agent(
        self,
        *,
        agent_id: str,
        reason: str,
        trace_id: str,
    ) -> AgentRecord:
        del reason, trace_id
        normalized_agent_id = agent_id.strip()
        if not normalized_agent_id:
            raise AgentRegistryRepositoryError(
                code="agent_registry_quarantine_invalid_id",
                message="agent_id must not be blank for quarantine",
            )
        record = self.agents.get(normalized_agent_id)
        if record is None:
            raise AgentRegistryRepositoryError(
                code="agent_registry_not_found",
                message=f"agent not found for quarantine: {normalized_agent_id}",
            )
        updated = replace(
            record,
            status="inactive",
            updated_at=datetime.now(tz=UTC),
        )
        self.agents[normalized_agent_id] = updated
        return updated


def _make_agent(
    tmp_path: Path,
) -> tuple[
    AdministratorAgent,
    DocumentPolicyEnforcer,
    RetentionEnforcer,
    InMemoryProjectArtifactRepository,
    InMemoryAuditWriter,
    _StubAgentRegistryRepo,
]:
    repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
    audit_writer = InMemoryAuditWriter()
    agent_registry_repo = _StubAgentRegistryRepo(
        agents={
            "agent-001": AgentRecord(
                agent_id="agent-001",
                role="specialist",
                agent_type="project_workforce",
                status="active",
                created_at=datetime.now(tz=UTC),
                updated_at=datetime.now(tz=UTC),
            )
        }
    )
    document_policy = DocumentPolicyEnforcer(
        governance_repo=repo,
        audit_writer=audit_writer,
        trace_id_factory=lambda: "generated-trace",
    )
    retention = RetentionEnforcer(
        governance_repo=repo,
        audit_writer=audit_writer,
        trace_id_factory=lambda: "generated-trace",
    )
    agent = AdministratorAgent(
        document_policy=document_policy,
        retention=retention,
        governance_repo=repo,
        agent_registry_repo=agent_registry_repo,  # type: ignore[arg-type]
        audit_writer=audit_writer,
        trace_id_factory=lambda: "generated-trace",
    )
    return agent, document_policy, retention, repo, audit_writer, agent_registry_repo


def _request(
    *,
    action: str,
    project_id: str | None = "proj-001",
    agent_id: str | None = None,
    artifact_type: str | None = None,
    reason: str = "policy check",
    severity: str = "high",
    rule_ids: tuple[str, ...] = ("STR-008",),
    trace_id: str = "trace-001",
) -> AdministratorRequest:
    return AdministratorRequest(
        action=action,
        project_id=project_id,
        agent_id=agent_id,
        artifact_type=artifact_type,
        reason=reason,
        severity=severity,
        rule_ids=rule_ids,
        trace_id=trace_id,
    )


def _latest_payload(
    repo: InMemoryProjectArtifactRepository,
    *,
    project_id: str,
    artifact_type: str,
) -> dict[str, object]:
    document = repo.read_latest_artifact(project_id, artifact_type)
    assert document is not None
    return json.loads(document.content)


class TestAdministratorDocumentPolicy:
    def test_artifact_cap_blocked_at_limit(self, tmp_path: Path) -> None:
        agent, _, _, repo, _, _ = _make_agent(tmp_path)
        for index in range(32):
            repo.write_project_artifact(
                project_id="proj-001",
                artifact_type="auditor_finding",
                content=json.dumps({"index": index}),
                write_context=ProjectArtifactWriteContext(
                    actor_role="auditor",
                    project_status="active",
                ),
            )

        response = agent.handle(
            _request(
                action=" check_artifact_cap ",
                artifact_type="auditor_finding",
                severity="MEDIUM",
            )
        )

        assert response.action_taken == "cap_denied"
        assert "cap exceeded" in response.oversight_text

    def test_project_manager_blocked_from_project_charter(self, tmp_path: Path) -> None:
        _, document_policy, _, _, _, _ = _make_agent(tmp_path)

        allowed = document_policy.check_role_permission(
            actor_role=" project_manager ",
            artifact_type=" project_charter ",
            project_status="active",
        )

        assert allowed is False

    def test_hash_mismatch_blocks_write_and_emits_audit_event(self, tmp_path: Path) -> None:
        _, document_policy, _, _, audit_writer, _ = _make_agent(tmp_path)

        result = document_policy.check_hash_integrity(
            stored_hash="stored-hash",
            provided_hash="provided-hash",
            trace_id="trace-hash",
        )

        assert result.integrity_ok is False
        assert "content_hash mismatch" in (result.denial_reason or "")
        event = audit_writer.get_events()[-1]
        assert event.event_type == "hash_integrity_failure"
        assert event.rule_ids == ("STR-007", "STR-010")


class TestAdministratorContainment:
    def test_containment_quarantines_agent_and_notifies_owner_and_ceo(self, tmp_path: Path) -> None:
        agent, _, _, repo, audit_writer, agent_registry_repo = _make_agent(tmp_path)

        response = agent.handle(
            _request(
                action="quarantine_agent",
                project_id=None,
                agent_id=" agent-001 ",
                reason="runtime integrity incident",
                severity="critical",
                rule_ids=("AUTH-001", "GOV-001"),
            )
        )

        assert response.action_taken == "agent_quarantined"
        assert agent_registry_repo.agents["agent-001"].status == "inactive"
        assert (
            _latest_payload(
                repo,
                project_id="system",
                artifact_type="administrator_owner_notification",
            )["next_owner_role"]
            == "owner"
        )
        assert (
            _latest_payload(
                repo,
                project_id="system",
                artifact_type="administrator_ceo_notification",
            )["next_owner_role"]
            == "ceo"
        )
        assert (
            _latest_payload(
                repo,
                project_id="system",
                artifact_type="administrator_owner_alert",
            )["severity"]
            == "critical"
        )
        assert audit_writer.get_events()[-1].event_type == "administrator_containment"


class TestAdministratorRetention:
    def test_retention_audit_records_reference_correct_rule_ids(self, tmp_path: Path) -> None:
        agent, _, _, repo, audit_writer, _ = _make_agent(tmp_path)

        completed_response = agent.handle(
            _request(
                action="enforce_retention",
                reason="project completed successfully",
                rule_ids=("STR-001",),
            )
        )
        terminated_response = agent.handle(
            _request(
                action="enforce_retention",
                reason="project terminated by owner",
                rule_ids=("STR-001", "STR-002"),
                trace_id="trace-terminated",
            )
        )

        assert completed_response.action_taken == "retention_enforced"
        assert terminated_response.action_taken == "retention_enforced"
        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="administrator_retention",
        )
        assert payload["action"] == "terminated_project_archived"
        events = audit_writer.get_events()
        assert events[0].rule_ids == ("STR-001",)
        assert events[-1].rule_ids == ("STR-001", "STR-002")
