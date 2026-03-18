"""M14-WP2 — CEO Agent unit tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from openqilin.agents.ceo.agent import CeoAgent
from openqilin.agents.ceo.decision_writer import CeoDecisionWriter
from openqilin.agents.ceo.models import (
    CeoCoApprovalError,
    CeoProposalGateError,
    CeoRequest,
)
from openqilin.data_access.repositories.artifacts import ProjectArtifactWriteContext
from openqilin.llm_gateway.schemas.requests import LlmPolicyContext
from openqilin.llm_gateway.schemas.responses import LlmGatewayResponse
from tests.testing.infra_stubs import InMemoryProjectArtifactRepository

_POLICY_CONTEXT = LlmPolicyContext(
    policy_version="v2",
    policy_hash="test-policy",
    rule_ids=(),
)
_CSO_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="ceo",
    project_status="proposed",
)
_CWO_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="cwo",
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


def _make_llm(text: str) -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = _llm_response(text)
    return llm


def _make_agent(
    tmp_path: Path,
    *,
    llm_text: str = "approved: advance this proposal to owner co-approval.",
) -> tuple[CeoAgent, InMemoryProjectArtifactRepository, MagicMock]:
    repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
    llm = _make_llm(llm_text)
    agent = CeoAgent(
        llm_gateway=llm,
        decision_writer=CeoDecisionWriter(governance_repo=repo),
        governance_repo=repo,
        cso_agent=MagicMock(),
        trace_id_factory=lambda: "generated-trace",
    )
    return agent, repo, llm


def _request(
    *,
    intent: str,
    message: str = "Approve the product launch proposal.",
    context: dict[str, object] | None = None,
    proposal_id: str | None = None,
    cso_review_outcome: str | None = None,
) -> CeoRequest:
    return CeoRequest(
        message=message,
        intent=intent,
        context={
            "project_id": "proj-001",
            "project_scope": "Launch the governed MVP.",
            **dict(context or {}),
        },
        proposal_id=proposal_id,
        cso_review_outcome=cso_review_outcome,
        trace_id="trace-001",
    )


def _write_cso_review(
    repo: InMemoryProjectArtifactRepository,
    *,
    proposal_id: str,
    review_outcome: str,
    trace_id: str = "trace-cso",
    project_id: str = "proj-001",
    advisory_text: str = "CSO review record",
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
                "trace_id": trace_id,
            }
        ),
        write_context=_CSO_WRITE_CONTEXT,
    )


def _write_cwo_coapproval(
    repo: InMemoryProjectArtifactRepository,
    *,
    project_id: str = "proj-001",
    approval_type: str,
    artifact_type: str | None = None,
    trace_id: str = "trace-cwo",
) -> None:
    repo.write_project_artifact(
        project_id=project_id,
        artifact_type="cwo_coapproval",
        content=json.dumps(
            {
                "event_type": "cwo_coapproval",
                "approval_type": approval_type,
                "artifact_type": artifact_type,
                "trace_id": trace_id,
            }
        ),
        write_context=_CWO_WRITE_CONTEXT,
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


class TestCeoProposalReview:
    def test_approves_proposal_with_cso_aligned_review(self, tmp_path: Path) -> None:
        agent, repo, _ = _make_agent(
            tmp_path,
            llm_text="approved: advance this proposal to owner co-approval immediately.",
        )
        _write_cso_review(repo, proposal_id="prop-001", review_outcome="Aligned")

        response = agent.handle(
            _request(
                intent="MUTATION",
                proposal_id="prop-001",
                cso_review_outcome="Aligned",
            )
        )

        assert response.decision == "approved"
        assert response.routing_hint is None

    def test_denies_proposal_without_cso_review_record(self, tmp_path: Path) -> None:
        agent, repo, llm = _make_agent(tmp_path)

        with pytest.raises(CeoProposalGateError, match="GATE-005"):
            agent.handle(
                _request(
                    intent="MUTATION",
                    proposal_id="prop-missing",
                    cso_review_outcome="Aligned",
                )
            )

        assert repo.read_latest_artifact("proj-001", "ceo_proposal_decision") is None
        llm.complete.assert_not_called()

    def test_needs_revision_on_cso_needs_revision_outcome(self, tmp_path: Path) -> None:
        agent, repo, _ = _make_agent(
            tmp_path,
            llm_text="needs_revision: revise the budget assumptions and resubmit.",
        )
        _write_cso_review(repo, proposal_id="prop-002", review_outcome="Needs Revision")

        response = agent.handle(
            _request(
                intent="MUTATION",
                proposal_id="prop-002",
                cso_review_outcome="Needs Revision",
            )
        )

        assert response.decision == "needs_revision"
        assert "I suggest" not in response.advisory_text

    def test_blocks_on_third_strategic_conflict_without_override(self, tmp_path: Path) -> None:
        agent, repo, llm = _make_agent(tmp_path)
        for index in range(3):
            _write_cso_review(
                repo,
                proposal_id="prop-conflict",
                review_outcome="Strategic Conflict",
                trace_id=f"trace-cso-{index}",
            )

        with pytest.raises(CeoProposalGateError, match="GATE-003"):
            agent.handle(
                _request(
                    intent="MUTATION",
                    proposal_id="prop-conflict",
                    cso_review_outcome="Strategic Conflict",
                )
            )

        llm.complete.assert_not_called()

    def test_allows_third_strategic_conflict_with_override_flag(self, tmp_path: Path) -> None:
        agent, repo, _ = _make_agent(
            tmp_path,
            llm_text="approved: override recorded and proposal advances with executive rationale.",
        )
        for index in range(3):
            _write_cso_review(
                repo,
                proposal_id="prop-override",
                review_outcome="Strategic Conflict",
                trace_id=f"trace-cso-{index}",
            )

        response = agent.handle(
            _request(
                intent="MUTATION",
                proposal_id="prop-override",
                cso_review_outcome="Strategic Conflict",
                context={"override_flag": True},
            )
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="ceo_proposal_decision",
        )
        assert response.decision == "approved"
        assert payload["override_flag"] is True

    def test_decision_persisted_with_trace_id_and_rationale(self, tmp_path: Path) -> None:
        agent, repo, _ = _make_agent(
            tmp_path,
            llm_text="approved: accept the proposal and document the rationale.",
        )
        _write_cso_review(repo, proposal_id="prop-003", review_outcome="Aligned")

        agent.handle(
            _request(
                intent="MUTATION",
                proposal_id="prop-003",
                cso_review_outcome="Aligned",
            )
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="ceo_proposal_decision",
        )
        assert payload["trace_id"] == "trace-001"
        assert "accept the proposal" in payload["rationale"]

    def test_decision_includes_revision_cycle_count(self, tmp_path: Path) -> None:
        agent, repo, _ = _make_agent(
            tmp_path,
            llm_text="approved: proposal can advance after recorded revisions.",
        )
        _write_cso_review(repo, proposal_id="prop-004", review_outcome="Strategic Conflict")
        CeoDecisionWriter(governance_repo=repo).write_proposal_decision(
            proposal_id="prop-004",
            project_id="proj-001",
            decision="needs_revision",
            rationale="Revise once more.",
            cso_review_outcome="Needs Revision",
            revision_cycle_count=1,
            override_flag=False,
            trace_id="trace-prior",
        )
        _write_cso_review(repo, proposal_id="prop-004", review_outcome="Aligned")

        agent.handle(
            _request(
                intent="MUTATION",
                proposal_id="prop-004",
                cso_review_outcome="Aligned",
            )
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="ceo_proposal_decision",
        )
        assert payload["revision_cycle_count"] == 2


class TestCeoDirective:
    def test_discussion_returns_directive_not_advisory(self, tmp_path: Path) -> None:
        agent, _, _ = _make_agent(
            tmp_path,
            llm_text="I suggest freezing the portfolio until dependencies stabilize.",
        )

        response = agent.handle(
            _request(
                intent="DISCUSSION",
                proposal_id=None,
                message="Confirm the current executive posture for launch sequencing.",
            )
        )

        assert response.routing_hint is None
        assert "I suggest" not in response.advisory_text
        assert response.advisory_text.startswith("Decision:")

    def test_workforce_intent_routes_to_cwo(self, tmp_path: Path) -> None:
        agent, _, llm = _make_agent(tmp_path)

        response = agent.handle(
            _request(
                intent="QUERY",
                proposal_id=None,
                message="We need to hire two specialists for the workforce plan.",
            )
        )

        assert response.routing_hint == "cwo"
        assert "route to cwo" in response.advisory_text.lower()
        llm.complete.assert_not_called()

    def test_strategy_question_routes_to_cso(self, tmp_path: Path) -> None:
        agent, _, llm = _make_agent(tmp_path)

        response = agent.handle(
            _request(
                intent="QUERY",
                proposal_id=None,
                message="What is the right portfolio strategy for next quarter?",
            )
        )

        assert response.routing_hint == "cso"
        assert "route to cso" in response.advisory_text.lower()
        llm.complete.assert_not_called()

    def test_structural_exception_routes_to_owner(self, tmp_path: Path) -> None:
        agent, _, llm = _make_agent(tmp_path)

        response = agent.handle(
            _request(
                intent="DISCUSSION",
                proposal_id=None,
                message="This is a structural exception that needs constitutional handling.",
            )
        )

        assert response.routing_hint == "owner"
        assert "Escalate to owner" in response.advisory_text
        llm.complete.assert_not_called()


class TestCeoCoApproval:
    def test_coapproval_denied_without_cwo_evidence(self, tmp_path: Path) -> None:
        agent, repo, llm = _make_agent(tmp_path)

        with pytest.raises(CeoCoApprovalError, match="ORCH-005"):
            agent.handle(
                _request(
                    intent="ADMIN",
                    proposal_id=None,
                    context={
                        "project_id": "proj-001",
                        "approval_type": "controlled_doc_edit",
                        "artifact_type": "scope_statement",
                    },
                )
            )

        assert repo.read_latest_artifact("proj-001", "ceo_coapproval") is None
        llm.complete.assert_not_called()

    def test_coapproval_succeeds_with_cwo_evidence_present(self, tmp_path: Path) -> None:
        agent, repo, _ = _make_agent(
            tmp_path,
            llm_text="approved: CEO co-approval recorded for the governed document edit.",
        )
        _write_cwo_coapproval(
            repo,
            approval_type="controlled_doc_edit",
            artifact_type="scope_statement",
        )

        response = agent.handle(
            _request(
                intent="ADMIN",
                proposal_id=None,
                context={
                    "project_id": "proj-001",
                    "approval_type": "controlled_doc_edit",
                    "artifact_type": "scope_statement",
                },
            )
        )

        assert response.decision == "approved"
        assert response.routing_hint is None

    def test_coapproval_writes_governance_record(self, tmp_path: Path) -> None:
        agent, repo, _ = _make_agent(
            tmp_path,
            llm_text="approved: CEO co-approval recorded for project completion.",
        )
        _write_cwo_coapproval(repo, approval_type="project_completion")

        agent.handle(
            _request(
                intent="ADMIN",
                proposal_id=None,
                context={
                    "project_id": "proj-001",
                    "approval_type": "project_completion",
                },
            )
        )

        payload = _latest_payload(repo, project_id="proj-001", artifact_type="ceo_coapproval")
        assert payload["approval_type"] == "project_completion"
        assert payload["event_type"] == "ceo_coapproval"


class TestCeoDecisionWriter:
    def test_write_proposal_decision_includes_all_gate_fields(self, tmp_path: Path) -> None:
        repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        writer = CeoDecisionWriter(governance_repo=repo)

        writer.write_proposal_decision(
            proposal_id="prop-writer",
            project_id="proj-001",
            decision="approved",
            rationale="Executive rationale.",
            cso_review_outcome="Aligned",
            revision_cycle_count=2,
            override_flag=True,
            trace_id="trace-writer",
        )

        payload = _latest_payload(
            repo,
            project_id="proj-001",
            artifact_type="ceo_proposal_decision",
        )
        assert payload["event_type"] == "ceo_proposal_decision"
        assert payload["proposal_id"] == "prop-writer"
        assert payload["decision"] == "approved"
        assert payload["rationale"] == "Executive rationale."
        assert payload["cso_review_outcome"] == "Aligned"
        assert payload["revision_cycle_count"] == 2
        assert payload["override_flag"] is True
        assert payload["trace_id"] == "trace-writer"
        assert payload["created_at"]

    def test_write_coapproval_record_includes_approval_type(self, tmp_path: Path) -> None:
        repo = InMemoryProjectArtifactRepository(system_root=tmp_path / "artifacts")
        writer = CeoDecisionWriter(governance_repo=repo)

        writer.write_coapproval_record(
            project_id="proj-001",
            approval_type="controlled_doc_edit",
            artifact_type="budget_plan",
            trace_id="trace-coapproval",
        )

        payload = _latest_payload(repo, project_id="proj-001", artifact_type="ceo_coapproval")
        assert payload["approval_type"] == "controlled_doc_edit"
        assert payload["artifact_type"] == "budget_plan"
