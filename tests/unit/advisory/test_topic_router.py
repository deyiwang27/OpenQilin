"""Unit tests for deterministic advisory topic routing."""

from __future__ import annotations

from openqilin.control_plane.advisory.topic_router import AdvisoryTopicRouter


def test_classify_budget_keyword() -> None:
    decision = AdvisoryTopicRouter().classify("what is my budget outlook?")

    assert decision is not None
    assert decision.agent_role == "auditor"
    assert decision.confidence == "high"


def test_classify_spend_keyword() -> None:
    decision = AdvisoryTopicRouter().classify("show spend this month")

    assert decision is not None
    assert decision.agent_role == "auditor"


def test_auditor_payment_keyword() -> None:
    decision = AdvisoryTopicRouter().classify("show payment history for this vendor")

    assert decision is not None
    assert decision.agent_role == "auditor"


def test_classify_strategic_keyword() -> None:
    decision = AdvisoryTopicRouter().classify("portfolio alignment review")

    assert decision is not None
    assert decision.agent_role == "cso"


def test_cso_review_keyword() -> None:
    decision = AdvisoryTopicRouter().classify("conduct a strategic review of cross-project risk")

    assert decision is not None
    assert decision.agent_role == "cso"


def test_classify_task_keyword() -> None:
    decision = AdvisoryTopicRouter().classify("what tasks are blocked?")

    assert decision is not None
    assert decision.agent_role == "project_manager"


def test_pm_status_keyword() -> None:
    decision = AdvisoryTopicRouter().classify("give me the project status and timeline")

    assert decision is not None
    assert decision.agent_role == "project_manager"


def test_classify_ceo_keyword() -> None:
    decision = AdvisoryTopicRouter().classify("I need executive approval")

    assert decision is not None
    assert decision.agent_role == "ceo"


def test_ceo_approval_keyword() -> None:
    decision = AdvisoryTopicRouter().classify("request approval before we decide")

    assert decision is not None
    assert decision.agent_role == "ceo"


def test_administrator_keywords_route_correctly() -> None:
    decision = AdvisoryTopicRouter().classify("what is the infrastructure health status")

    assert decision is not None
    assert decision.agent_role == "administrator"


def test_administrator_infra_keyword() -> None:
    decision = AdvisoryTopicRouter().classify("check infra logs")

    assert decision is not None
    assert decision.agent_role == "administrator"


def test_classify_cwo_keyword() -> None:
    decision = AdvisoryTopicRouter().classify("workforce plan update")

    assert decision is not None
    assert decision.agent_role == "cwo"


def test_cwo_activate_keyword() -> None:
    decision = AdvisoryTopicRouter().classify("activate onboarding for the new team headcount")

    assert decision is not None
    assert decision.agent_role == "cwo"


def test_classify_no_match() -> None:
    assert AdvisoryTopicRouter().classify("hello how are you") is None


def test_classify_case_insensitive() -> None:
    decision = AdvisoryTopicRouter().classify("BUDGET COMPLIANCE")

    assert decision is not None
    assert decision.agent_role == "auditor"


def test_classify_most_matches_wins() -> None:
    decision = AdvisoryTopicRouter().classify("budget spend strategy")

    assert decision is not None
    assert decision.agent_role == "auditor"
    assert set(decision.matched_keywords) == {"budget", "spend"}


def test_classify_tie_returns_none() -> None:
    assert AdvisoryTopicRouter().classify("budget strategic") is None


def test_classify_empty_string() -> None:
    assert AdvisoryTopicRouter().classify("") is None
