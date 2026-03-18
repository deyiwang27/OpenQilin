"""M13-WP7: CSO Rewrite — Chief Strategy Officer unit tests.

(File kept at m12_wp8 path for historical traceability; content updated for WP7.)

Coverage:
- CSOAgent handles proposal review when proposal_id present
- CSOAgent handles cross-project advisory (no proposal_id)
- Strategic Conflict detected → CSOConflictFlag with escalate_to="ceo"
- Needs Revision detected → CSOConflictFlag with escalate_to=None
- Aligned outcome → no conflict_flag
- GATE-006: governance record persisted when proposal_id + project_id present
- GATE-006: governance record NOT persisted when proposal_id absent
- GATE-006: governance record NOT persisted when project_id absent
- strategic_note set on Strategic Conflict
- CSOAgent has no reference to PolicyRuntimeClient or OPAPolicyRuntimeClient
- CSOAgent can be constructed without OPA (no assert_opa_client_required)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from openqilin.agents.cso.agent import CSOAgent
from openqilin.agents.cso.models import CSORequest, CSOResponse
from openqilin.control_plane.grammar.models import ChatContext, IntentClass
from openqilin.llm_gateway.schemas.requests import LlmPolicyContext
from openqilin.llm_gateway.schemas.responses import LlmGatewayResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_POLICY_CONTEXT_STUB = LlmPolicyContext(
    policy_version="v2",
    policy_hash="test-hash",
    rule_ids=(),
)


def _llm_response(text: str) -> LlmGatewayResponse:
    return LlmGatewayResponse(
        request_id="req-test",
        trace_id="trace-test",
        decision="served",
        model_selected="gemini-test",
        usage=None,
        cost=None,
        budget_usage=None,
        budget_context_effective=None,
        quota_limit_source="policy_guardrail",
        latency_ms=1,
        policy_context=_POLICY_CONTEXT_STUB,
        generated_text=text,
    )


def _stub_llm(text: str = "This proposal is Aligned with portfolio strategy.") -> Any:
    llm = MagicMock()
    llm.complete.return_value = _llm_response(text)
    return llm


def _stub_project_artifact_repo() -> Any:
    return MagicMock()


def _stub_governance_repo(project_status: str = "active") -> Any:
    repo = MagicMock()
    project = MagicMock()
    project.status = project_status
    project.title = "Test Project"
    repo.get_project.return_value = project
    return repo


def _make_request(
    intent: IntentClass = IntentClass.DISCUSSION,
    message: str = "Should we expand project alpha?",
    proposal_id: str | None = None,
    project_id: str | None = "proj-001",
    portfolio_context: str | None = None,
) -> CSORequest:
    return CSORequest(
        message=message,
        intent=intent,
        context=ChatContext(chat_class="institutional", channel_id="ch-001", project_id=project_id),
        trace_id="trace-wp7-001",
        proposal_id=proposal_id,
        portfolio_context=portfolio_context,
    )


def _make_agent(
    llm_text: str = "This proposal is Aligned with portfolio strategy.",
) -> CSOAgent:
    return CSOAgent(
        llm_gateway=_stub_llm(llm_text),
        project_artifact_repo=_stub_project_artifact_repo(),
        governance_repo=_stub_governance_repo(),
    )


# ---------------------------------------------------------------------------
# CSOAgent: general advisory (no proposal_id)
# ---------------------------------------------------------------------------


class TestCSOCrossProjectAdvisory:
    def test_discussion_intent_returns_cso_response(self) -> None:
        agent = _make_agent()
        request = _make_request(intent=IntentClass.DISCUSSION)

        response = agent.handle(request)

        assert isinstance(response, CSOResponse)
        assert response.intent_confirmed == IntentClass.DISCUSSION
        assert response.trace_id == request.trace_id

    def test_query_intent_returns_cso_response(self) -> None:
        agent = _make_agent()
        request = _make_request(intent=IntentClass.QUERY)

        response = agent.handle(request)

        assert isinstance(response, CSOResponse)
        assert response.advisory_text

    def test_no_proposal_id_no_governance_record_written(self) -> None:
        artifact_repo = _stub_project_artifact_repo()
        agent = CSOAgent(
            llm_gateway=_stub_llm(),
            project_artifact_repo=artifact_repo,
            governance_repo=_stub_governance_repo(),
        )
        request = _make_request(proposal_id=None)

        agent.handle(request)

        artifact_repo.write_project_artifact.assert_not_called()

    def test_advisory_uses_llm(self) -> None:
        llm = _stub_llm("Strategic perspective: balanced.")
        agent = CSOAgent(
            llm_gateway=llm,
            project_artifact_repo=_stub_project_artifact_repo(),
            governance_repo=_stub_governance_repo(),
        )
        request = _make_request()

        response = agent.handle(request)

        llm.complete.assert_called_once()
        assert response.advisory_text == "Strategic perspective: balanced."


# ---------------------------------------------------------------------------
# CSOAgent: proposal review (proposal_id present)
# ---------------------------------------------------------------------------


class TestCSOProposalReview:
    def test_proposal_review_returns_cso_response(self) -> None:
        agent = _make_agent("This proposal is Aligned with the current portfolio.")
        request = _make_request(proposal_id="prop-001")

        response = agent.handle(request)

        assert isinstance(response, CSOResponse)
        assert response.conflict_flag is None  # Aligned → no flag

    def test_strategic_conflict_sets_conflict_flag(self) -> None:
        agent = _make_agent(
            "Strategic Conflict: this proposal conflicts with the committed Q2 roadmap. "
            "Escalation to CEO required."
        )
        request = _make_request(proposal_id="prop-002")

        response = agent.handle(request)

        assert response.conflict_flag is not None
        assert response.conflict_flag.flag_type == "strategic_conflict"
        assert response.conflict_flag.escalate_to == "ceo"

    def test_needs_revision_sets_conflict_flag(self) -> None:
        agent = _make_agent(
            "This proposal needs revision before it can advance. "
            "Addressable: timeline and resource allocation should be clarified."
        )
        request = _make_request(proposal_id="prop-003")

        response = agent.handle(request)

        assert response.conflict_flag is not None
        assert response.conflict_flag.flag_type == "needs_revision"
        assert response.conflict_flag.escalate_to is None

    def test_aligned_outcome_no_conflict_flag(self) -> None:
        agent = _make_agent("This proposal is fully Aligned with portfolio objectives.")
        request = _make_request(proposal_id="prop-004")

        response = agent.handle(request)

        assert response.conflict_flag is None

    def test_strategic_conflict_sets_strategic_note(self) -> None:
        agent = _make_agent("Strategic Conflict: incompatible with existing commitments.")
        request = _make_request(proposal_id="prop-005")

        response = agent.handle(request)

        assert response.strategic_note is not None
        assert "CEO" in response.strategic_note


# ---------------------------------------------------------------------------
# GATE-006: governance record persistence
# ---------------------------------------------------------------------------


class TestGate006GovernanceRecordPersistence:
    def test_proposal_review_writes_governance_record(self) -> None:
        """GATE-006: CSO review record persisted when proposal_id + project_id present."""
        artifact_repo = _stub_project_artifact_repo()
        agent = CSOAgent(
            llm_gateway=_stub_llm("Aligned."),
            project_artifact_repo=artifact_repo,
            governance_repo=_stub_governance_repo(),
        )
        request = _make_request(proposal_id="prop-gate006", project_id="proj-001")

        agent.handle(request)

        artifact_repo.write_project_artifact.assert_called_once()
        call_kwargs = artifact_repo.write_project_artifact.call_args.kwargs
        assert call_kwargs["project_id"] == "proj-001"
        assert call_kwargs["artifact_type"] == "cso_review"
        assert "prop-gate006" in call_kwargs["content"]

    def test_no_governance_record_when_project_id_absent(self) -> None:
        """GATE-006: record cannot be written without project_id; error surfaced in strategic_note."""
        artifact_repo = _stub_project_artifact_repo()
        agent = CSOAgent(
            llm_gateway=_stub_llm("Aligned."),
            project_artifact_repo=artifact_repo,
            governance_repo=_stub_governance_repo(),
        )
        request = _make_request(proposal_id="prop-gate006", project_id=None)

        response = agent.handle(request)

        artifact_repo.write_project_artifact.assert_not_called()
        assert response.strategic_note is not None
        assert "GATE-006" in response.strategic_note
        assert "MUST NOT advance" in response.strategic_note

    def test_governance_record_content_includes_trace_id(self) -> None:
        artifact_repo = _stub_project_artifact_repo()
        agent = CSOAgent(
            llm_gateway=_stub_llm("Aligned."),
            project_artifact_repo=artifact_repo,
            governance_repo=_stub_governance_repo(),
        )
        request = _make_request(proposal_id="prop-trace", project_id="proj-001")

        agent.handle(request)

        call_kwargs = artifact_repo.write_project_artifact.call_args.kwargs
        assert request.trace_id in call_kwargs["content"]

    def test_governance_record_content_includes_review_outcome(self) -> None:
        artifact_repo = _stub_project_artifact_repo()
        agent = CSOAgent(
            llm_gateway=_stub_llm("Strategic Conflict detected. Escalation to CEO required."),
            project_artifact_repo=artifact_repo,
            governance_repo=_stub_governance_repo(),
        )
        request = _make_request(proposal_id="prop-conflict", project_id="proj-001")

        agent.handle(request)

        call_kwargs = artifact_repo.write_project_artifact.call_args.kwargs
        assert "Strategic Conflict" in call_kwargs["content"]

    def test_governance_record_write_failure_does_not_block_advisory(self) -> None:
        """GATE-006 write failure is logged but does not raise; advisory still returned."""
        artifact_repo = _stub_project_artifact_repo()
        artifact_repo.write_project_artifact.side_effect = RuntimeError("db down")
        agent = CSOAgent(
            llm_gateway=_stub_llm("Aligned."),
            project_artifact_repo=artifact_repo,
            governance_repo=_stub_governance_repo(),
        )
        request = _make_request(proposal_id="prop-failwrite", project_id="proj-001")

        # Should not raise even if write fails
        response = agent.handle(request)

        assert isinstance(response, CSOResponse)


# ---------------------------------------------------------------------------
# CSOAgent: no OPA dependency
# ---------------------------------------------------------------------------


class TestCSONoOpaDependency:
    def test_cso_constructed_without_opa_client(self) -> None:
        """CSOAgent must not require an OPAPolicyRuntimeClient (WP7: OPA dep removed)."""
        agent = CSOAgent(
            llm_gateway=_stub_llm(),
            project_artifact_repo=_stub_project_artifact_repo(),
            governance_repo=_stub_governance_repo(),
        )
        assert isinstance(agent, CSOAgent)

    def test_cso_agent_module_has_no_assert_opa_client_required(self) -> None:
        """assert_opa_client_required must not exist in the CSO agent module (WP7 removal)."""
        import openqilin.agents.cso.agent as cso_module

        assert not hasattr(cso_module, "assert_opa_client_required")

    def test_cso_agent_has_no_policy_client_attribute(self) -> None:
        agent = CSOAgent(
            llm_gateway=_stub_llm(),
            project_artifact_repo=_stub_project_artifact_repo(),
            governance_repo=_stub_governance_repo(),
        )
        assert not hasattr(agent, "_policy_client")

    def test_cso_handles_all_intent_classes_without_opa(self) -> None:
        """All intent classes must be handled without OPA evaluation."""
        for intent in IntentClass:
            agent = _make_agent()
            request = _make_request(intent=intent)
            response = agent.handle(request)
            assert isinstance(response, CSOResponse)
