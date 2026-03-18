"""M13-WP5 — Domain Leader Virtual Agent.

Unit tests for:
- DL rejects requests without project_id.
- DL dispatch_command always raises DomainLeaderCommandDeniedError.
- DL returns DomainLeaderResponse without writing to Discord channel.
- DL escalation to PM on domain risk (not directly to CWO).
- DL specialist clarification path.
- DL specialist review outcomes.
- EscalationHandler wraps DL correctly.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from openqilin.agents.domain_leader.agent import DomainLeaderAgent
from openqilin.agents.domain_leader.escalation_handler import EscalationHandler
from openqilin.agents.domain_leader.models import (
    DomainLeaderCommandDeniedError,
    DomainLeaderProjectContextError,
    DomainLeaderRequest,
    SpecialistReviewRequest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_llm_gateway(text: str = "Domain assessment: all good.") -> MagicMock:
    response = MagicMock()
    response.decision = "served"
    response.generated_text = text
    llm = MagicMock()
    llm.complete.return_value = response
    return llm


def _make_dl_request(
    project_id: str = "proj-1",
    message: str = "Escalation: specialist blocked on data format",
    trace_id: str = "trace-1",
) -> DomainLeaderRequest:
    return DomainLeaderRequest(
        project_id=project_id,
        message=message,
        requesting_agent="project_manager",
        trace_id=trace_id,
        task_id="t-1",
    )


# ---------------------------------------------------------------------------
# Project context enforcement
# ---------------------------------------------------------------------------


class TestDomainLeaderProjectContextEnforcement:
    def test_handle_escalation_rejects_empty_project_id(self) -> None:
        dl = DomainLeaderAgent(llm_gateway=MagicMock())
        request = DomainLeaderRequest(
            project_id="",
            message="test",
            requesting_agent="project_manager",
            trace_id="trace-1",
        )
        with pytest.raises(DomainLeaderProjectContextError) as exc_info:
            dl.handle_escalation(request)
        assert exc_info.value.code == "dl_project_context_required"

    def test_handle_clarification_rejects_empty_project_id(self) -> None:
        dl = DomainLeaderAgent(llm_gateway=MagicMock())
        with pytest.raises(DomainLeaderProjectContextError):
            dl.handle_clarification_request(
                specialist_id="spec-1",
                question="What format?",
                task_id="t-1",
                project_id="",
                trace_id="trace-1",
            )

    def test_review_specialist_output_rejects_empty_project_id(self) -> None:
        dl = DomainLeaderAgent(llm_gateway=MagicMock())
        review = SpecialistReviewRequest(
            task_id="t-1",
            project_id="",
            specialist_output="output text",
            trace_id="trace-1",
        )
        with pytest.raises(DomainLeaderProjectContextError):
            dl.review_specialist_output(review)


# ---------------------------------------------------------------------------
# command: deny enforcement
# ---------------------------------------------------------------------------


class TestDomainLeaderCommandDeny:
    def test_dispatch_command_always_raises(self) -> None:
        dl = DomainLeaderAgent(llm_gateway=MagicMock())
        with pytest.raises(DomainLeaderCommandDeniedError) as exc_info:
            dl.dispatch_command("spec-backend-dev")
        assert exc_info.value.code == "dl_command_denied"
        assert "spec-backend-dev" in str(exc_info.value)

    def test_dispatch_command_denied_for_any_specialist(self) -> None:
        dl = DomainLeaderAgent(llm_gateway=MagicMock())
        for specialist in ("spec-1", "spec-2", "backend", "data-analyst"):
            with pytest.raises(DomainLeaderCommandDeniedError):
                dl.dispatch_command(specialist)


# ---------------------------------------------------------------------------
# Escalation handling
# ---------------------------------------------------------------------------


class TestDomainLeaderEscalation:
    def test_handle_escalation_returns_dl_response(self) -> None:
        llm = _make_llm_gateway("All resolved. No further action needed.")
        dl = DomainLeaderAgent(llm_gateway=llm)
        request = _make_dl_request()
        response = dl.handle_escalation(request)

        assert response.trace_id == request.trace_id
        assert response.advisory_text == "All resolved. No further action needed."
        assert response.domain_outcome == "resolved"
        assert response.escalate_to is None

    def test_handle_escalation_domain_risk_escalates_to_pm_not_cwo(self) -> None:
        """Material domain risk must escalate to PM, not directly to CWO."""
        llm = _make_llm_gateway("Risk assessment: ESCALATE_TO_PM — domain risk too high.")
        dl = DomainLeaderAgent(llm_gateway=llm)
        response = dl.handle_escalation(_make_dl_request())

        assert response.domain_outcome == "domain_risk_escalation"
        assert response.escalate_to == "project_manager"
        assert response.escalate_to != "cwo"

    def test_handle_escalation_needs_rework(self) -> None:
        llm = _make_llm_gateway("Output quality insufficient. NEEDS_REWORK: reformat the schema.")
        dl = DomainLeaderAgent(llm_gateway=llm)
        response = dl.handle_escalation(_make_dl_request())

        assert response.domain_outcome == "needs_rework"
        assert response.rework_recommendations is not None


# ---------------------------------------------------------------------------
# Specialist review
# ---------------------------------------------------------------------------


class TestDomainLeaderSpecialistReview:
    def test_review_allow_outcome(self) -> None:
        llm = _make_llm_gateway("ALLOW — output meets domain quality standards.")
        dl = DomainLeaderAgent(llm_gateway=llm)
        review = SpecialistReviewRequest(
            task_id="t-1",
            project_id="proj-1",
            specialist_output="The schema is correct and follows the v2 spec.",
            trace_id="trace-1",
        )
        outcome = dl.review_specialist_output(review)
        assert outcome.outcome == "allow"
        assert outcome.rework_recommendations is None

    def test_review_needs_rework_outcome(self) -> None:
        llm = _make_llm_gateway("NEEDS_REWORK: the schema is missing field `created_at`.")
        dl = DomainLeaderAgent(llm_gateway=llm)
        review = SpecialistReviewRequest(
            task_id="t-1",
            project_id="proj-1",
            specialist_output="Schema delivered.",
            trace_id="trace-2",
        )
        outcome = dl.review_specialist_output(review)
        assert outcome.outcome == "needs_rework"
        assert outcome.rework_recommendations is not None


# ---------------------------------------------------------------------------
# Specialist clarification
# ---------------------------------------------------------------------------


class TestDomainLeaderClarificationPath:
    def test_clarification_returns_domain_response(self) -> None:
        llm = _make_llm_gateway("Use ISO 8601 format for all timestamps.")
        dl = DomainLeaderAgent(llm_gateway=llm)
        response = dl.handle_clarification_request(
            specialist_id="spec-data-1",
            question="Which timestamp format should I use?",
            task_id="t-42",
            project_id="proj-alpha",
            trace_id="trace-99",
        )
        assert response.advisory_text == "Use ISO 8601 format for all timestamps."
        assert response.domain_outcome == "resolved"
        assert response.escalate_to is None

    def test_clarification_uses_project_context(self) -> None:
        """LLM is called with the project_id in context."""
        llm = _make_llm_gateway("Use the standard format.")
        dl = DomainLeaderAgent(llm_gateway=llm)
        dl.handle_clarification_request(
            specialist_id="spec-1",
            question="question",
            task_id="t-1",
            project_id="proj-specific",
            trace_id="trace-1",
        )
        call_args = llm.complete.call_args
        assert "proj-specific" in call_args[0][0].project_id


# ---------------------------------------------------------------------------
# EscalationHandler
# ---------------------------------------------------------------------------


class TestEscalationHandler:
    def test_escalation_handler_wraps_dl(self) -> None:
        llm = _make_llm_gateway("Assessment: resolved.")
        dl = DomainLeaderAgent(llm_gateway=llm)
        handler = EscalationHandler(domain_leader=dl)
        response = handler.escalate(
            project_id="proj-1",
            message="PM escalation: data pipeline issue",
            trace_id="trace-1",
            task_id="t-7",
        )
        assert response.domain_outcome == "resolved"

    def test_escalation_handler_default_requesting_agent_is_pm(self) -> None:
        llm = _make_llm_gateway("OK.")
        dl = DomainLeaderAgent(llm_gateway=llm)
        handler = EscalationHandler(domain_leader=dl)
        handler.escalate(project_id="proj-1", message="issue", trace_id="trace-1")
        call_args = llm.complete.call_args
        prompt = call_args[0][0].messages_or_prompt
        assert "project_manager" in prompt
