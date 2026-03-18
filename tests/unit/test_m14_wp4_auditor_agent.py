"""M14-WP4 — Auditor Agent unit tests."""

from __future__ import annotations

import json
from pathlib import Path

from openqilin.agents.auditor.agent import AuditorAgent
from openqilin.agents.auditor.enforcement import AuditorEnforcementService
from openqilin.agents.auditor.models import AuditorRequest
from openqilin.observability.testing.stubs import InMemoryAuditWriter
from openqilin.task_orchestrator.admission.envelope_validator import AdmissionEnvelope
from openqilin.task_orchestrator.services.lifecycle_service import TaskLifecycleService
from tests.testing.infra_stubs import (
    InMemoryCommunicationRepository,
    InMemoryProjectArtifactRepository,
    InMemoryRuntimeStateRepository,
)


def _make_agent(
    tmp_path: Path,
) -> tuple[
    AuditorAgent,
    AuditorEnforcementService,
    InMemoryProjectArtifactRepository,
    InMemoryRuntimeStateRepository,
    InMemoryAuditWriter,
]:
    repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
    runtime_state_repo = InMemoryRuntimeStateRepository()
    audit_writer = InMemoryAuditWriter()
    enforcement = AuditorEnforcementService(
        lifecycle_service=TaskLifecycleService(runtime_state_repo=runtime_state_repo),
        governance_repo=repo,
        audit_writer=audit_writer,
        communication_repo=InMemoryCommunicationRepository(),  # type: ignore[arg-type]
    )
    agent = AuditorAgent(
        enforcement=enforcement,
        governance_repo=repo,
        audit_writer=audit_writer,
        trace_id_factory=lambda: "generated-trace",
    )
    return agent, enforcement, repo, runtime_state_repo, audit_writer


def _request(
    *,
    event_type: str,
    task_id: str | None = "task-001",
    project_id: str | None = "proj-001",
    severity: str = "high",
    rule_ids: tuple[str, ...] = ("AUD-001", "ESC-001"),
    rationale: str = "Violation detected.",
    source_agent_role: str | None = "project_manager",
    trace_id: str = "trace-001",
) -> AuditorRequest:
    return AuditorRequest(
        event_type=event_type,
        task_id=task_id,
        project_id=project_id,
        severity=severity,
        rule_ids=rule_ids,
        rationale=rationale,
        source_agent_role=source_agent_role,
        trace_id=trace_id,
    )


def _seed_task(
    runtime_state_repo: InMemoryRuntimeStateRepository,
    *,
    task_id_suffix: str = "001",
    project_id: str = "proj-001",
) -> str:
    task = runtime_state_repo.create_task_from_envelope(
        AdmissionEnvelope(
            request_id=f"req-{task_id_suffix}",
            trace_id=f"trace-{task_id_suffix}",
            principal_id="pm-001",
            principal_role="project_manager",
            trust_domain="discord",
            connector="discord",
            command="dispatch",
            target="specialist",
            args=("run",),
            metadata=(),
            project_id=project_id,
            idempotency_key=f"idem-{task_id_suffix}",
        )
    )
    return task.task_id


def _latest_payload(
    repo: InMemoryProjectArtifactRepository,
    *,
    project_id: str,
    artifact_type: str,
) -> dict[str, object]:
    document = repo.read_latest_artifact(project_id, artifact_type)
    assert document is not None
    return json.loads(document.content)


class TestAuditorBudgetBreach:
    def test_budget_breach_pauses_task_when_task_id_present(self, tmp_path: Path) -> None:
        agent, _, _, runtime_state_repo, _ = _make_agent(tmp_path)
        task_id = _seed_task(runtime_state_repo)

        response = agent.handle(
            _request(
                event_type="budget_breach",
                task_id=task_id,
                rule_ids=("BUD-001", "ESC-003"),
                rationale="Hard budget threshold exceeded.",
            )
        )

        task = runtime_state_repo.get_task_by_id(task_id)
        assert task is not None
        assert task.status == "blocked"
        assert task.outcome_error_code == "auditor_enforcement"
        assert response.action_taken == "task_paused"

    def test_budget_breach_writes_ceo_notification(self, tmp_path: Path) -> None:
        agent, _, repo, runtime_state_repo, _ = _make_agent(tmp_path)
        task_id = _seed_task(runtime_state_repo)

        agent.handle(
            _request(
                event_type="budget_breach",
                task_id=task_id,
                rule_ids=("BUD-001", "ESC-005"),
                rationale="Budget lock triggered.",
            )
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="auditor_ceo_notification",
        )
        assert payload["event_type"] == "auditor_ceo_notification"
        assert payload["task_id"] == task_id

    def test_budget_breach_critical_writes_owner_alert(self, tmp_path: Path) -> None:
        agent, _, repo, runtime_state_repo, _ = _make_agent(tmp_path)
        task_id = _seed_task(runtime_state_repo)

        agent.handle(
            _request(
                event_type="budget_breach",
                task_id=task_id,
                severity="critical",
                rule_ids=("BUD-001", "ESC-006"),
                rationale="Critical budget overrun detected.",
            )
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="auditor_owner_alert",
        )
        assert payload["severity"] == "critical"
        assert payload["task_id"] == task_id

    def test_budget_breach_escalates_to_owner(self, tmp_path: Path) -> None:
        agent, _, repo, runtime_state_repo, _ = _make_agent(tmp_path)
        task_id = _seed_task(runtime_state_repo)

        agent.handle(
            _request(
                event_type="budget_breach",
                task_id=task_id,
                rule_ids=("BUD-001", "ESC-003"),
                rationale="Budget breach requires owner escalation.",
            )
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="auditor_owner_escalation",
        )
        assert payload["rule_ids"] == ["BUD-001", "ESC-003"]
        assert payload["rationale"] == "Budget breach requires owner escalation."

    def test_budget_breach_without_task_id_escalates_owner_only(self, tmp_path: Path) -> None:
        agent, _, repo, _, _ = _make_agent(tmp_path)

        response = agent.handle(
            _request(
                event_type="budget_breach",
                task_id=None,
                rule_ids=("BUD-001", "ESC-003"),
                rationale="Budget breach without a routed task.",
            )
        )

        assert response.action_taken == "owner_escalated"
        assert repo.read_latest_artifact("proj-001", "auditor_owner_escalation") is not None
        assert repo.read_latest_artifact("proj-001", "auditor_finding") is not None
        assert repo.read_latest_artifact("proj-001", "auditor_ceo_notification") is None


class TestAuditorGovernanceViolation:
    def test_governance_violation_writes_immutable_finding(self, tmp_path: Path) -> None:
        agent, _, repo, _, _ = _make_agent(tmp_path)

        response = agent.handle(
            _request(
                event_type="governance_violation",
                rule_ids=("GOV-001", "ESC-002"),
                rationale="Governance boundary exceeded.",
            )
        )

        payload = _latest_payload(repo, project_id="proj-001", artifact_type="auditor_finding")
        assert response.finding_id is not None
        assert payload["finding_type"] == "governance_violation"

    def test_governance_violation_escalates_to_owner(self, tmp_path: Path) -> None:
        agent, _, repo, _, _ = _make_agent(tmp_path)

        agent.handle(
            _request(
                event_type="governance_violation",
                rule_ids=("GOV-001", "ESC-002"),
                rationale="Owner review required.",
            )
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="auditor_owner_escalation",
        )
        assert payload["next_owner_role"] == "owner"
        assert payload["rationale"] == "Owner review required."

    def test_governance_high_severity_notifies_ceo(self, tmp_path: Path) -> None:
        agent, _, repo, _, _ = _make_agent(tmp_path)

        agent.handle(
            _request(
                event_type="governance_violation",
                severity="high",
                rule_ids=("GOV-001", "ESC-005"),
                rationale="High-severity governance incident.",
            )
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="auditor_ceo_notification",
        )
        assert payload["incident_type"] == "governance_violation"


class TestAuditorBehavioralViolation:
    def test_behavioral_violation_escalates_directly_to_owner(self, tmp_path: Path) -> None:
        agent, _, repo, _, _ = _make_agent(tmp_path)

        response = agent.handle(
            _request(
                event_type="behavioral_violation",
                rule_ids=("ESC-008", "AUD-001"),
                rationale="Behavioral violation detected.",
                source_agent_role="specialist",
            )
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="auditor_owner_escalation",
        )
        assert response.action_taken == "owner_escalated"
        assert payload["current_owner_role"] == "auditor"
        assert payload["next_owner_role"] == "owner"

    def test_behavioral_violation_notifies_ceo(self, tmp_path: Path) -> None:
        agent, _, repo, _, _ = _make_agent(tmp_path)

        agent.handle(
            _request(
                event_type="behavioral_violation",
                rule_ids=("ESC-008", "ESC-005"),
                rationale="Behavioral incident for executive awareness.",
                source_agent_role="specialist",
            )
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="auditor_ceo_notification",
        )
        assert payload["incident_type"] == "behavioral_violation"

    def test_behavioral_violation_pm_bypass_does_not_route_through_pm(self, tmp_path: Path) -> None:
        agent, _, repo, _, _ = _make_agent(tmp_path)

        agent.handle(
            _request(
                event_type="behavioral_violation",
                rule_ids=("ESC-008",),
                rationale="Project manager violation must bypass PM.",
                source_agent_role="project_manager",
            )
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="auditor_owner_escalation",
        )
        assert payload["path_reference"] == "auditor->owner"
        assert repo.read_latest_artifact("proj-001", "decision_log") is None

    def test_behavioral_violation_duplicate_suppressed_without_new_evidence(
        self, tmp_path: Path
    ) -> None:
        agent, enforcement, repo, _, _ = _make_agent(tmp_path)
        enforcement.record_finding(
            project_id="proj-001",
            finding_type="behavioral_violation",
            rule_ids=("ESC-008",),
            rationale="Existing behavioral finding.",
            trace_id="trace-existing",
            task_id="task-dup",
            source_agent_role="project_manager",
            severity="high",
        )

        response = agent.handle(
            _request(
                event_type="behavioral_violation",
                task_id="task-dup",
                rule_ids=("ESC-008",),
                rationale="Existing behavioral finding.",
                source_agent_role="project_manager",
            )
        )

        assert response.action_taken == "no_action"
        assert (
            len(
                repo.list_artifact_documents(project_id="proj-001", artifact_type="auditor_finding")
            )
            == 1
        )
        assert repo.read_latest_artifact("proj-001", "auditor_owner_escalation") is None

    def test_behavioral_violation_writes_immutable_finding(self, tmp_path: Path) -> None:
        agent, _, repo, _, _ = _make_agent(tmp_path)

        agent.handle(
            _request(
                event_type="behavioral_violation",
                rule_ids=("ESC-008",),
                rationale="Behavioral finding must be immutable.",
                source_agent_role="project_manager",
            )
        )

        payload = _latest_payload(repo, project_id="proj-001", artifact_type="auditor_finding")
        assert payload["finding_type"] == "behavioral_violation"
        assert payload["source_agent_role"] == "project_manager"


class TestAuditorDocumentViolation:
    def test_document_cap_violation_writes_finding(self, tmp_path: Path) -> None:
        agent, _, repo, _, _ = _make_agent(tmp_path)

        agent.handle(
            _request(
                event_type="document_violation",
                rule_ids=("DOC-001",),
                rationale="Document cap exceeded.",
                source_agent_role="administrator",
            )
        )

        payload = _latest_payload(repo, project_id="proj-001", artifact_type="auditor_finding")
        assert payload["finding_type"] == "document_violation"

    def test_document_cap_violation_escalates_to_owner(self, tmp_path: Path) -> None:
        agent, _, repo, _, _ = _make_agent(tmp_path)

        agent.handle(
            _request(
                event_type="document_violation",
                rule_ids=("DOC-001", "ESC-002"),
                rationale="Document integrity breach.",
                source_agent_role="administrator",
            )
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="auditor_owner_escalation",
        )
        assert payload["rule_ids"] == ["DOC-001", "ESC-002"]


class TestAuditorAuthorityProfile:
    def test_auditor_cannot_issue_commands(self, tmp_path: Path) -> None:
        agent, _, _, _, _ = _make_agent(tmp_path)

        response = agent.handle(_request(event_type="query", task_id=None))

        assert response.action_taken != "task_executed"
        assert "command" not in response.advisory_text.lower()
        assert "execute" not in response.advisory_text.lower()

    def test_auditor_cannot_approve_or_deny(self, tmp_path: Path) -> None:
        agent, _, _, _, _ = _make_agent(tmp_path)

        response = agent.handle(
            _request(
                event_type="governance_violation",
                rationale="Authority profile language check.",
            )
        )

        lowered = response.advisory_text.lower()
        assert "approve" not in lowered
        assert "deny" not in lowered
        assert "decision" not in lowered

    def test_auditor_query_returns_no_action(self, tmp_path: Path) -> None:
        agent, _, repo, _, _ = _make_agent(tmp_path)

        response = agent.handle(_request(event_type="query", task_id=None))

        assert response.action_taken == "no_action"
        assert repo.read_latest_artifact("proj-001", "auditor_finding") is None


class TestAuditorEnforcementService:
    def test_pause_task_transitions_to_blocked(self, tmp_path: Path) -> None:
        _, enforcement, _, runtime_state_repo, _ = _make_agent(tmp_path)
        task_id = _seed_task(runtime_state_repo)

        enforcement.pause_task(
            task_id,
            project_id="proj-001",
            reason="Pause this task.",
            severity="high",
            rule_ids=("ESC-005",),
            trace_id="trace-enforcement",
        )

        task = runtime_state_repo.get_task_by_id(task_id)
        assert task is not None
        assert task.status == "blocked"

    def test_pause_task_writes_enforcement_finding(self, tmp_path: Path) -> None:
        _, enforcement, repo, runtime_state_repo, audit_writer = _make_agent(tmp_path)
        task_id = _seed_task(runtime_state_repo)

        enforcement.pause_task(
            task_id,
            project_id="proj-001",
            reason="Pause with immutable evidence.",
            severity="high",
            rule_ids=("ESC-005",),
            trace_id="trace-enforcement",
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="auditor_enforcement",
        )
        assert payload["task_id"] == task_id
        assert audit_writer.get_events()[-1].event_type == "auditor_enforcement"

    def test_pause_task_critical_writes_owner_alert(self, tmp_path: Path) -> None:
        _, enforcement, repo, runtime_state_repo, _ = _make_agent(tmp_path)
        task_id = _seed_task(runtime_state_repo)

        enforcement.pause_task(
            task_id,
            project_id="proj-001",
            reason="Critical impact pause.",
            severity="critical",
            rule_ids=("ESC-006",),
            trace_id="trace-critical",
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="auditor_owner_alert",
        )
        assert payload["severity"] == "critical"

    def test_escalate_to_owner_includes_trace_rule_rationale(self, tmp_path: Path) -> None:
        _, enforcement, repo, _, _ = _make_agent(tmp_path)

        enforcement.escalate_to_owner(
            project_id="proj-001",
            rule_ids=("ESC-001", "ESC-002"),
            rationale="Escalation rationale.",
            severity="high",
            trace_id="trace-owner",
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="auditor_owner_escalation",
        )
        assert payload["trace_id"] == "trace-owner"
        assert payload["rule_ids"] == ["ESC-001", "ESC-002"]
        assert payload["rationale"] == "Escalation rationale."

    def test_record_finding_is_append_only(self, tmp_path: Path) -> None:
        _, enforcement, repo, _, _ = _make_agent(tmp_path)

        first_id = enforcement.record_finding(
            project_id="proj-001",
            finding_type="document_violation",
            rule_ids=("DOC-001",),
            rationale="First finding.",
            trace_id="trace-1",
            severity="medium",
        )
        second_id = enforcement.record_finding(
            project_id="proj-001",
            finding_type="document_violation",
            rule_ids=("DOC-001",),
            rationale="Second finding.",
            trace_id="trace-2",
            severity="medium",
        )

        documents = repo.list_artifact_documents(
            project_id="proj-001", artifact_type="auditor_finding"
        )
        assert len(documents) == 2
        assert documents[0].pointer.revision_no == 1
        assert documents[1].pointer.revision_no == 2
        assert first_id != second_id
