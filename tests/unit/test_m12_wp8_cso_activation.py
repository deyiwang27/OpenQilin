"""M12-WP8: CSO Activation tests.

Coverage:
- CSO governance gate raises CSOPolicyError when policy returns deny
- CSO governance gate returns CSOResponse when policy allows
- Advisory/query intents skip policy evaluation and return a response directly
- assert_opa_client_required raises RuntimeError for InMemoryPolicyRuntimeClient
- assert_opa_client_required does NOT raise for OPAPolicyRuntimeClient
- CSO is present in RuntimeServices built in dev mode (no OPA URL)
- CSO activation guard fires when opa_url is set but OPA client is not real
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from openqilin.agents.cso.agent import CSOAgent, assert_opa_client_required
from openqilin.agents.cso.models import CSOPolicyError, CSORequest, CSOResponse
from openqilin.control_plane.grammar.models import ChatContext, IntentClass
from openqilin.llm_gateway.schemas.requests import LlmPolicyContext
from openqilin.llm_gateway.schemas.responses import LlmGatewayResponse
from openqilin.policy_runtime_integration.models import PolicyEvaluationResult
from openqilin.policy_runtime_integration.testing.in_memory_client import (
    InMemoryPolicyRuntimeClient,
)


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


def _make_request(intent: IntentClass, message: str = "test message") -> CSORequest:
    return CSORequest(
        message=message,
        intent=intent,
        context=ChatContext(chat_class="institutional", channel_id="ch-001"),
        principal_role="owner",
        trace_id="trace-wp8-001",
    )


def _stub_deny_policy() -> object:
    """Return a policy client that always denies."""
    client = MagicMock()
    client.evaluate.return_value = PolicyEvaluationResult(
        decision="deny",
        reason_code="test_deny",
        reason_message="denied by test",
        policy_version="v2",
        policy_hash="test-hash",
        rule_ids=("TEST-RULE-001",),
    )
    return client


def _stub_allow_policy() -> object:
    """Return a policy client that always allows."""
    client = MagicMock()
    client.evaluate.return_value = PolicyEvaluationResult(
        decision="allow",
        reason_code="test_allow",
        reason_message="allowed by test",
        policy_version="v2",
        policy_hash="test-hash",
        rule_ids=("TEST-RULE-001",),
    )
    return client


def _stub_llm(text: str = "governance advisory response") -> object:
    """Return an LLM gateway that always returns the given text."""
    llm = MagicMock()
    llm.complete.return_value = _llm_response(text)
    return llm


# ---------------------------------------------------------------------------
# CSOAgent: mutation intent — policy DENY → CSOPolicyError
# ---------------------------------------------------------------------------


class TestCSOGovernanceDeny:
    def test_mutation_intent_denied_by_policy_raises_cso_policy_error(self) -> None:
        agent = CSOAgent(llm_gateway=_stub_llm(), policy_client=_stub_deny_policy())
        request = _make_request(IntentClass.MUTATION, "delete all projects")

        with pytest.raises(CSOPolicyError) as exc_info:
            agent.handle(request)

        assert exc_info.value.code == "cso_governance_denied"

    def test_mutation_deny_error_message_includes_rule_id(self) -> None:
        agent = CSOAgent(llm_gateway=_stub_llm(), policy_client=_stub_deny_policy())
        request = _make_request(IntentClass.MUTATION, "reset state")

        with pytest.raises(CSOPolicyError) as exc_info:
            agent.handle(request)

        assert "TEST-RULE-001" in exc_info.value.message

    def test_admin_intent_denied_by_policy_raises_cso_policy_error(self) -> None:
        agent = CSOAgent(llm_gateway=_stub_llm(), policy_client=_stub_deny_policy())
        request = _make_request(IntentClass.ADMIN, "promote user to administrator")

        with pytest.raises(CSOPolicyError) as exc_info:
            agent.handle(request)

        assert exc_info.value.code == "cso_governance_denied"

    def test_mutation_deny_does_not_call_llm(self) -> None:
        llm = _stub_llm()
        agent = CSOAgent(llm_gateway=llm, policy_client=_stub_deny_policy())
        request = _make_request(IntentClass.MUTATION)

        with pytest.raises(CSOPolicyError):
            agent.handle(request)

        llm.complete.assert_not_called()


# ---------------------------------------------------------------------------
# CSOAgent: mutation intent — policy ALLOW → CSOResponse
# ---------------------------------------------------------------------------


class TestCSOGovernanceAllow:
    def test_mutation_intent_allowed_returns_cso_response(self) -> None:
        agent = CSOAgent(llm_gateway=_stub_llm(), policy_client=_stub_allow_policy())
        request = _make_request(IntentClass.MUTATION)

        response = agent.handle(request)

        assert isinstance(response, CSOResponse)
        assert response.intent_confirmed == IntentClass.MUTATION
        assert response.trace_id == request.trace_id

    def test_mutation_allowed_includes_governance_note(self) -> None:
        agent = CSOAgent(llm_gateway=_stub_llm(), policy_client=_stub_allow_policy())
        request = _make_request(IntentClass.MUTATION)

        response = agent.handle(request)

        assert response.governance_note is not None
        assert "/oq" in response.governance_note

    def test_mutation_allowed_calls_llm(self) -> None:
        llm = _stub_llm("advisory text")
        agent = CSOAgent(llm_gateway=llm, policy_client=_stub_allow_policy())
        request = _make_request(IntentClass.MUTATION)

        response = agent.handle(request)

        llm.complete.assert_called_once()
        assert response.advisory_text == "advisory text"


# ---------------------------------------------------------------------------
# CSOAgent: advisory/query intents — skip policy evaluation
# ---------------------------------------------------------------------------


class TestCSOAdvisoryIntents:
    def test_discussion_intent_skips_policy_evaluation(self) -> None:
        policy_client = _stub_deny_policy()
        agent = CSOAgent(llm_gateway=_stub_llm(), policy_client=policy_client)
        request = _make_request(IntentClass.DISCUSSION)

        # Should NOT raise even though the policy client would deny
        response = agent.handle(request)

        assert isinstance(response, CSOResponse)
        policy_client.evaluate.assert_not_called()

    def test_query_intent_skips_policy_evaluation(self) -> None:
        policy_client = _stub_deny_policy()
        agent = CSOAgent(llm_gateway=_stub_llm(), policy_client=policy_client)
        request = _make_request(IntentClass.QUERY)

        response = agent.handle(request)

        assert isinstance(response, CSOResponse)
        policy_client.evaluate.assert_not_called()

    def test_advisory_response_has_no_governance_note_for_discussion(self) -> None:
        agent = CSOAgent(llm_gateway=_stub_llm(), policy_client=_stub_allow_policy())
        request = _make_request(IntentClass.DISCUSSION)

        response = agent.handle(request)

        assert response.governance_note is None

    def test_admin_intent_evaluates_policy(self) -> None:
        policy_client = _stub_allow_policy()
        agent = CSOAgent(llm_gateway=_stub_llm(), policy_client=policy_client)
        request = _make_request(IntentClass.ADMIN)

        agent.handle(request)

        policy_client.evaluate.assert_called_once()


# ---------------------------------------------------------------------------
# assert_opa_client_required: startup guard
# ---------------------------------------------------------------------------


class TestAssertOpaClientRequired:
    def test_raises_for_in_memory_policy_client(self) -> None:
        in_memory = InMemoryPolicyRuntimeClient()

        with pytest.raises(RuntimeError) as exc_info:
            assert_opa_client_required(in_memory)

        assert "CSO must not be activated without real OPA client" in str(exc_info.value)

    def test_raises_for_arbitrary_mock_client(self) -> None:
        fake_client = MagicMock()

        with pytest.raises(RuntimeError):
            assert_opa_client_required(fake_client)

    def test_does_not_raise_for_opa_runtime_client(self) -> None:
        from openqilin.policy_runtime_integration.client import OPAPolicyRuntimeClient

        real_opa = OPAPolicyRuntimeClient(opa_url="http://localhost:8181")

        # Guard should pass — no exception
        assert_opa_client_required(real_opa)


# ---------------------------------------------------------------------------
# CSO wired into RuntimeServices (dev mode — no opa_url)
# ---------------------------------------------------------------------------


class TestCSOInRuntimeServices:
    def test_cso_agent_present_in_dev_runtime_services(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("OPENQILIN_SYSTEM_ROOT", str(tmp_path / "system_root"))
        monkeypatch.delenv("OPENQILIN_OPA_URL", raising=False)

        from openqilin.control_plane.api.dependencies import build_runtime_services

        services = build_runtime_services()

        assert isinstance(services.cso_agent, CSOAgent)

    def test_cso_activation_guard_called_when_opa_url_set(self, monkeypatch, tmp_path) -> None:
        """When opa_url is set, build_runtime_services calls assert_opa_client_required."""
        from unittest.mock import patch

        monkeypatch.setenv("OPENQILIN_SYSTEM_ROOT", str(tmp_path / "system_root"))
        monkeypatch.setenv("OPENQILIN_OPA_URL", "http://opa.test:8181")

        from openqilin.control_plane.api.dependencies import build_runtime_services

        guard_calls: list = []

        def _capture_guard(client: object) -> None:
            guard_calls.append(client)

        with patch(
            "openqilin.control_plane.api.dependencies.assert_opa_client_required",
            side_effect=_capture_guard,
        ):
            build_runtime_services()

        assert len(guard_calls) == 1, "assert_opa_client_required must be called exactly once"
        from openqilin.policy_runtime_integration.client import OPAPolicyRuntimeClient

        assert isinstance(guard_calls[0], OPAPolicyRuntimeClient)
