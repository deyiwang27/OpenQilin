"""M14-WP3 — CWO Agent unit tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from openqilin.agents.ceo.models import CeoResponse
from openqilin.agents.cso.models import CSOConflictFlag, CSOResponse
from openqilin.agents.cwo.agent import CwoAgent
from openqilin.agents.cwo.models import (
    CwoApprovalChainError,
    CwoCommandError,
    CwoRequest,
)
from openqilin.agents.cwo.workforce_initializer import WorkforceInitializer
from openqilin.data_access.repositories.artifacts import ProjectArtifactWriteContext
from openqilin.llm_gateway.schemas.requests import LlmPolicyContext
from openqilin.llm_gateway.schemas.responses import LlmGatewayResponse
from tests.testing.infra_stubs import InMemoryProjectArtifactRepository

_POLICY_CONTEXT = LlmPolicyContext(
    policy_version="v2",
    policy_hash="test-policy",
    rule_ids=(),
)
_CEO_PROPOSAL_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="ceo",
    project_status="proposed",
)
_CEO_ACTIVE_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="ceo",
    project_status="active",
)
_CWO_APPROVED_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="cwo",
    project_status="approved",
)
_OWNER_APPROVED_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="owner",
    project_status="approved",
)
_PROJECT_MANAGER_ACTIVE_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="project_manager",
    project_status="active",
)


def _llm_response(text: str) -> LlmGatewayResponse:
    return LlmGatewayResponse(
        request_id="req-1",
        trace_id="trace-1",
        decision="served",
        model_selected="gemini-test",
        usage=None,
        cost=None,
        budget_usage=None,
        budget_context_effective=None,
        quota_limit_source="policy_guardrail",
        latency_ms=1,
        policy_context=_POLICY_CONTEXT,
        generated_text=text,
    )


def _make_llm(*texts: str) -> MagicMock:
    llm = MagicMock()
    if texts:
        llm.complete.side_effect = [_llm_response(text) for text in texts]
    else:
        llm.complete.return_value = _llm_response("Command: workforce posture confirmed.")
    return llm


def _make_data_access(project_status: str = "approved") -> MagicMock:
    data_access = MagicMock()
    data_access.get_project_snapshot.return_value = MagicMock(
        project_id="proj-001",
        status=project_status,
        title="Project Test",
        active_task_count=3,
        blocked_task_count=1,
    )
    return data_access


def _make_agent(
    tmp_path: Path,
    *,
    llm_texts: tuple[str, ...] = ("Command: workforce posture confirmed.",),
    cso_agent: Any | None = None,
    ceo_agent: Any | None = None,
    agent_registry_repo: Any | None = None,
    artifact_repo: InMemoryProjectArtifactRepository | None = None,
    project_status: str = "approved",
) -> tuple[CwoAgent, InMemoryProjectArtifactRepository, MagicMock, Any]:
    repo = artifact_repo or InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
    registry_repo = agent_registry_repo or MagicMock()
    llm = _make_llm(*llm_texts)
    initializer = WorkforceInitializer(
        governance_repo=repo,
        agent_registry_repo=registry_repo,
    )
    agent = CwoAgent(
        llm_gateway=llm,
        cso_agent=cso_agent or MagicMock(),
        ceo_agent=ceo_agent or MagicMock(),
        workforce_initializer=initializer,
        governance_repo=repo,
        data_access=_make_data_access(project_status=project_status),  # type: ignore[arg-type]
        trace_id_factory=lambda: "generated-trace",
    )
    return agent, repo, llm, registry_repo


def _request(
    *,
    intent: str,
    message: str = "Prepare the workforce package.",
    project_id: str | None = "proj-001",
    context: dict[str, object] | None = None,
) -> CwoRequest:
    return CwoRequest(
        message=message,
        intent=intent,
        project_id=project_id,
        context=dict(context or {}),
        trace_id="trace-001",
    )


def _latest_payload(
    repo: InMemoryProjectArtifactRepository,
    *,
    project_id: str,
    artifact_type: str,
) -> dict[str, Any]:
    document = repo.read_latest_artifact(project_id, artifact_type)
    assert document is not None
    return json.loads(document.content)


def _write_cso_review(
    repo: InMemoryProjectArtifactRepository,
    *,
    proposal_id: str = "prop-001",
    review_outcome: str = "Aligned",
    project_id: str = "proj-001",
    advisory_text: str = "CSO review record.",
) -> None:
    repo.write_project_artifact(
        project_id=project_id,
        artifact_type="cso_review",
        content=json.dumps(
            {
                "event_type": "cso_review_outcome",
                "proposal_id": proposal_id,
                "review_outcome": review_outcome,
                "cso_advisory_text": advisory_text,
                "trace_id": "trace-cso",
            }
        ),
        write_context=_CEO_PROPOSAL_WRITE_CONTEXT,
    )


def _write_ceo_proposal_decision(
    repo: InMemoryProjectArtifactRepository,
    *,
    decision: str = "approved",
    project_id: str = "proj-001",
    proposal_id: str = "prop-001",
) -> None:
    repo.write_project_artifact(
        project_id=project_id,
        artifact_type="ceo_proposal_decision",
        content=json.dumps(
            {
                "event_type": "ceo_proposal_decision",
                "proposal_id": proposal_id,
                "decision": decision,
                "trace_id": "trace-ceo",
            }
        ),
        write_context=_CEO_PROPOSAL_WRITE_CONTEXT,
    )


def _write_owner_coapproval(
    repo: InMemoryProjectArtifactRepository, *, project_id: str = "proj-001"
) -> None:
    repo.write_project_artifact(
        project_id=project_id,
        artifact_type="decision_log",
        content=json.dumps(
            {
                "event_type": "owner_coapproval",
                "trace_id": "trace-owner",
            }
        ),
        write_context=_OWNER_APPROVED_WRITE_CONTEXT,
    )


def _write_completion_report(
    repo: InMemoryProjectArtifactRepository,
    *,
    project_id: str = "proj-001",
) -> None:
    repo.write_project_artifact(
        project_id=project_id,
        artifact_type="completion_report",
        content="Completion report: governed delivery complete.",
        write_context=_PROJECT_MANAGER_ACTIVE_WRITE_CONTEXT,
    )


def _write_ceo_coapproval(
    repo: InMemoryProjectArtifactRepository,
    *,
    approval_type: str = "controlled_doc_edit",
    project_id: str = "proj-001",
    artifact_type: str | None = "scope_statement",
) -> None:
    repo.write_project_artifact(
        project_id=project_id,
        artifact_type="ceo_coapproval",
        content=json.dumps(
            {
                "event_type": "ceo_coapproval",
                "approval_type": approval_type,
                "artifact_type": artifact_type,
                "trace_id": "trace-ceo",
            }
        ),
        write_context=_CEO_ACTIVE_WRITE_CONTEXT,
    )


class _CSOStub:
    def __init__(
        self, repo: InMemoryProjectArtifactRepository, *, review_outcome: str = "Aligned"
    ) -> None:
        self._repo = repo
        self._review_outcome = review_outcome
        self.calls: list[Any] = []

    def handle(self, request: Any) -> CSOResponse:
        self.calls.append(request)
        _write_cso_review(
            self._repo,
            proposal_id=request.proposal_id,
            review_outcome=self._review_outcome,
            project_id=request.context.project_id or "proj-001",
            advisory_text=f"CSO outcome: {self._review_outcome}",
        )
        conflict_flag = None
        if self._review_outcome == "Needs Revision":
            conflict_flag = CSOConflictFlag(flag_type="needs_revision", reason="Revise scope")
        elif self._review_outcome == "Strategic Conflict":
            conflict_flag = CSOConflictFlag(
                flag_type="strategic_conflict",
                reason="Strategic conflict",
                escalate_to="ceo",
            )
        return CSOResponse(
            advisory_text=f"CSO outcome: {self._review_outcome}",
            intent_confirmed=request.intent,
            trace_id=request.trace_id,
            strategic_note=None,
            conflict_flag=conflict_flag,
        )


class _CEOStub:
    def __init__(self, *, decision: str = "approved") -> None:
        self._decision = decision
        self.calls: list[Any] = []

    def handle(self, request: Any) -> CeoResponse:
        self.calls.append(request)
        return CeoResponse(
            decision=self._decision,
            advisory_text=f"Decision: {self._decision}.",
            routing_hint=None,
            trace_id=request.trace_id,
        )


class TestCwoProposalFlow:
    def test_proposal_flow_triggers_cso_review(self, tmp_path: Path) -> None:
        repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        cso_agent = _CSOStub(repo)
        ceo_agent = _CEOStub()
        agent, _, _, _ = _make_agent(
            tmp_path,
            llm_texts=("Command: workforce package drafted.",),
            cso_agent=cso_agent,
            ceo_agent=ceo_agent,
            artifact_repo=repo,
        )

        response = agent.handle(
            _request(
                intent="MUTATION",
                context={
                    "action": "submit_proposal",
                    "proposal_id": "prop-001",
                    "project_scope": "Launch the governed MVP.",
                },
            )
        )

        assert response.action_taken == "proposal_submitted"
        assert len(cso_agent.calls) == 1
        assert cso_agent.calls[0].proposal_id == "prop-001"

    def test_proposal_flow_presents_ceo_with_cso_outcome(self, tmp_path: Path) -> None:
        repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        cso_agent = _CSOStub(repo, review_outcome="Needs Revision")
        ceo_agent = _CEOStub(decision="needs_revision")
        agent, _, _, _ = _make_agent(
            tmp_path,
            llm_texts=("Command: workforce package drafted.",),
            cso_agent=cso_agent,
            ceo_agent=ceo_agent,
            artifact_repo=repo,
        )

        agent.handle(
            _request(
                intent="MUTATION",
                context={
                    "action": "submit_proposal",
                    "proposal_id": "prop-002",
                    "project_scope": "Launch the governed MVP.",
                },
            )
        )

        assert len(ceo_agent.calls) == 1
        assert ceo_agent.calls[0].cso_review_outcome == "Needs Revision"

    def test_proposal_flow_returns_pending_when_ceo_approves(self, tmp_path: Path) -> None:
        repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        agent, _, _, _ = _make_agent(
            tmp_path,
            llm_texts=("Command: workforce package drafted.",),
            cso_agent=_CSOStub(repo),
            ceo_agent=_CEOStub(decision="approved"),
            artifact_repo=repo,
        )

        response = agent.handle(
            _request(
                intent="MUTATION",
                context={"action": "submit_proposal", "proposal_id": "prop-003"},
            )
        )

        assert response.action_taken == "proposal_submitted"
        assert response.workforce_status == "pending_owner_approval"

    def test_proposal_flow_returns_blocked_when_ceo_denies(self, tmp_path: Path) -> None:
        repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        agent, _, _, _ = _make_agent(
            tmp_path,
            llm_texts=("Command: workforce package drafted.",),
            cso_agent=_CSOStub(repo),
            ceo_agent=_CEOStub(decision="denied"),
            artifact_repo=repo,
        )

        response = agent.handle(
            _request(
                intent="MUTATION",
                context={"action": "submit_proposal", "proposal_id": "prop-004"},
            )
        )

        assert response.action_taken is None
        assert response.workforce_status == "blocked"


class TestCwoWorkforceInitialization:
    def test_initialization_requires_project_id(self, tmp_path: Path) -> None:
        agent, _, _, _ = _make_agent(tmp_path)

        with pytest.raises(CwoCommandError, match="project_id"):
            agent.handle(
                _request(
                    intent="MUTATION",
                    project_id=None,
                    context={"action": "initialize_workforce"},
                )
            )

    def test_initialization_requires_completion_report(self, tmp_path: Path) -> None:
        agent, repo, _, _ = _make_agent(tmp_path)
        _write_cso_review(repo)
        _write_ceo_proposal_decision(repo)

        with pytest.raises(CwoCommandError, match="completion_report"):
            agent.handle(
                _request(
                    intent="MUTATION",
                    context={
                        "action": "initialize_workforce",
                        "template": "pm-core",
                        "llm_profile": "dev_gemini_free",
                        "system_prompt_package": "pkg://pm-core",
                    },
                )
            )

    def test_initialization_rejected_without_approval_chain(self, tmp_path: Path) -> None:
        agent, repo, _, _ = _make_agent(tmp_path)
        _write_completion_report(repo)

        with pytest.raises(CwoApprovalChainError, match="missing approval evidence"):
            agent.handle(
                _request(
                    intent="MUTATION",
                    context={
                        "action": "initialize_workforce",
                        "template": "pm-core",
                        "llm_profile": "dev_gemini_free",
                        "system_prompt_package": "pkg://pm-core",
                    },
                )
            )

    def test_initialization_succeeds_with_full_approval_chain(self, tmp_path: Path) -> None:
        agent, repo, _, registry_repo = _make_agent(
            tmp_path,
            llm_texts=("Command: workforce initialized for governed execution.",),
        )
        _write_completion_report(repo)
        _write_cso_review(repo)
        _write_ceo_proposal_decision(repo)
        _write_owner_coapproval(repo)

        response = agent.handle(
            _request(
                intent="MUTATION",
                context={
                    "action": "initialize_workforce",
                    "template": "pm-core",
                    "llm_profile": "dev_gemini_free",
                    "system_prompt_package": "pkg://pm-core",
                },
            )
        )

        assert response.action_taken == "workforce_initialized"
        assert response.workforce_status == "initialized"
        registry_repo.bind_project_workforce.assert_called_once()

    def test_initialization_writes_workforce_plan_artifact(self, tmp_path: Path) -> None:
        agent, repo, _, _ = _make_agent(
            tmp_path,
            llm_texts=("Command: workforce initialized for governed execution.",),
        )
        _write_completion_report(repo)
        _write_cso_review(repo)
        _write_ceo_proposal_decision(repo)
        _write_owner_coapproval(repo)

        agent.handle(
            _request(
                intent="MUTATION",
                context={
                    "action": "initialize_workforce",
                    "template": "pm-core",
                    "llm_profile": "dev_gemini_free",
                    "system_prompt_package": "pkg://pm-core",
                },
            )
        )

        payload = _latest_payload(repo, project_id="proj-001", artifact_type="workforce_plan")
        assert payload["author_role"] == "cwo"
        assert payload["trace_id"] == "trace-001"

    def test_initialization_writes_project_charter_when_absent(self, tmp_path: Path) -> None:
        agent, repo, _, _ = _make_agent(
            tmp_path,
            llm_texts=("Command: workforce initialized for governed execution.",),
        )
        _write_completion_report(repo)
        _write_cso_review(repo)
        _write_ceo_proposal_decision(repo)
        _write_owner_coapproval(repo)

        agent.handle(
            _request(
                intent="MUTATION",
                context={
                    "action": "initialize_workforce",
                    "template": "pm-core",
                    "llm_profile": "dev_gemini_free",
                    "system_prompt_package": "pkg://pm-core",
                },
            )
        )

        payload = _latest_payload(repo, project_id="proj-001", artifact_type="project_charter")
        assert payload["author_role"] == "cwo"

    def test_initialization_records_cwo_coapproval(self, tmp_path: Path) -> None:
        agent, repo, _, _ = _make_agent(
            tmp_path,
            llm_texts=("Command: workforce initialized for governed execution.",),
        )
        _write_completion_report(repo)
        _write_cso_review(repo)
        _write_ceo_proposal_decision(repo)
        _write_owner_coapproval(repo)

        agent.handle(
            _request(
                intent="MUTATION",
                context={
                    "action": "initialize_workforce",
                    "approval_type": "project_completion",
                    "template": "pm-core",
                    "llm_profile": "dev_gemini_free",
                    "system_prompt_package": "pkg://pm-core",
                },
            )
        )

        payload = _latest_payload(repo, project_id="proj-001", artifact_type="cwo_coapproval")
        assert payload["event_type"] == "cwo_coapproval"
        assert payload["approval_type"] == "project_completion"


class TestCwoCoApproval:
    def test_coapproval_rejected_without_ceo_evidence(self, tmp_path: Path) -> None:
        agent, _, _, _ = _make_agent(tmp_path)

        with pytest.raises(CwoCommandError, match="CEO co-approval evidence"):
            agent.handle(
                _request(
                    intent="ADMIN",
                    context={
                        "approval_type": "controlled_doc_edit",
                        "artifact_type": "scope_statement",
                    },
                )
            )

    def test_coapproval_succeeds_with_ceo_evidence(self, tmp_path: Path) -> None:
        agent, repo, _, _ = _make_agent(tmp_path)
        _write_ceo_coapproval(repo)

        response = agent.handle(
            _request(
                intent="ADMIN",
                context={
                    "approval_type": "controlled_doc_edit",
                    "artifact_type": "scope_statement",
                },
            )
        )

        assert response.action_taken == "coapproval_recorded"
        assert response.advisory_text.startswith("Command:")

    def test_coapproval_writes_cwo_coapproval_record(self, tmp_path: Path) -> None:
        agent, repo, _, _ = _make_agent(tmp_path)
        _write_ceo_coapproval(repo)

        agent.handle(
            _request(
                intent="ADMIN",
                context={
                    "approval_type": "controlled_doc_edit",
                    "artifact_type": "scope_statement",
                },
            )
        )

        payload = _latest_payload(repo, project_id="proj-001", artifact_type="cwo_coapproval")
        assert payload["event_type"] == "cwo_coapproval"
        assert payload["artifact_type"] == "scope_statement"


class TestCwoStatus:
    def test_discussion_returns_command_framing_not_advisory(self, tmp_path: Path) -> None:
        agent, _, llm, _ = _make_agent(
            tmp_path,
            llm_texts=("I suggest reviewing workforce blockers before continuing.",),
        )

        response = agent.handle(_request(intent="DISCUSSION", message="Show workforce status."))

        assert "I suggest" not in response.advisory_text
        assert response.advisory_text.startswith("Status:")
        llm.complete.assert_called_once()

    def test_strategy_dispute_routes_to_cso(self, tmp_path: Path) -> None:
        agent, _, llm, _ = _make_agent(tmp_path)

        response = agent.handle(
            _request(
                intent="DISCUSSION",
                message="We have a domain strategy dispute across projects.",
            )
        )

        assert response.action_taken == "routed"
        assert "CSO" in response.advisory_text
        llm.complete.assert_not_called()

    def test_execution_risk_routes_to_pm(self, tmp_path: Path) -> None:
        agent, _, llm, _ = _make_agent(tmp_path)

        response = agent.handle(
            _request(
                intent="QUERY",
                message="There is an execution risk and delivery blocker on the milestone.",
            )
        )

        assert response.action_taken == "routed"
        assert "Project Manager" in response.advisory_text
        llm.complete.assert_not_called()

    def test_budget_blocker_routes_to_ceo(self, tmp_path: Path) -> None:
        agent, _, llm, _ = _make_agent(tmp_path)

        response = agent.handle(
            _request(
                intent="QUERY",
                message="We hit a budget blocker and funding blocker on this project.",
            )
        )

        assert response.action_taken == "routed"
        assert "CEO" in response.advisory_text
        llm.complete.assert_not_called()
