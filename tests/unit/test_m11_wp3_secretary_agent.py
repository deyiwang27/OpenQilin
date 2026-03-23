"""Unit tests for M11-WP3: Secretary Agent Activation.

Covers:
- SecretaryAgent.handle() returns advisory response for discussion intent
- SecretaryAgent.handle() returns advisory response for query intent
- SecretaryAgent.handle() rejects mutation intent (advisory policy profile)
- SecretaryAgent.handle() rejects admin intent (advisory policy profile)
- Secretary is NOT the default responder for project channel messages
  (FreeTextRouter routes project to project_manager, not secretary)
- Secretary membership active in leadership_council, governance, executive
"""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock

import pytest

from openqilin.agents.secretary.agent import SecretaryAgent
from openqilin.agents.secretary.models import SecretaryPolicyError, SecretaryRequest
from openqilin.control_plane.grammar.free_text_router import FreeTextRouter
from openqilin.control_plane.grammar.models import ChatContext, IntentClass
from openqilin.control_plane.identity.discord_governance import (
    _MEMBERSHIP_BY_CHAT_CLASS,
    _PENDING_ROLE_FLAGS,
)
from openqilin.llm_gateway.providers.litellm_adapter import InMemoryLiteLLMAdapter
from openqilin.llm_gateway.schemas.requests import LlmPolicyContext
from openqilin.llm_gateway.schemas.responses import LlmGatewayResponse
from openqilin.llm_gateway.service import LlmGatewayService
from openqilin.task_orchestrator.dispatch.llm_dispatch import (
    ConversationStoreProtocol,
    ConversationTurn,
)


_POLICY_CONTEXT = LlmPolicyContext(
    policy_version="v2",
    policy_hash="test-policy",
    rule_ids=(),
)


def _served_response(text: str) -> LlmGatewayResponse:
    return LlmGatewayResponse(
        request_id="req-1",
        trace_id="trace-1",
        decision="served",
        model_selected="model-test",
        usage=None,
        cost=None,
        budget_usage=None,
        budget_context_effective=None,
        quota_limit_source="policy_guardrail",
        latency_ms=1,
        policy_context=_POLICY_CONTEXT,
        generated_text=text,
    )


def _make_agent() -> SecretaryAgent:
    return SecretaryAgent(llm_gateway=LlmGatewayService(provider=InMemoryLiteLLMAdapter()))


def _ctx(chat_class: str, project_id: str | None = None) -> ChatContext:
    return ChatContext(chat_class=chat_class, channel_id="ch-test", project_id=project_id)


# ---------------------------------------------------------------------------
# Advisory response tests
# ---------------------------------------------------------------------------


class TestSecretaryAgentAdvisory:
    def setup_method(self) -> None:
        self.agent = _make_agent()

    def test_discussion_intent_returns_advisory_response(self) -> None:
        req = SecretaryRequest(
            message="What should we prioritize this week?",
            intent=IntentClass.DISCUSSION,
            context=_ctx("leadership_council"),
            trace_id="trace-wp3-001",
        )
        resp = self.agent.handle(req)
        assert resp.intent_confirmed == IntentClass.DISCUSSION
        assert resp.advisory_text  # non-empty (fallback or LLM)
        assert resp.trace_id == "trace-wp3-001"

    def test_query_intent_returns_advisory_response(self) -> None:
        req = SecretaryRequest(
            message="What is the status of Project Alpha?",
            intent=IntentClass.QUERY,
            context=_ctx("governance"),
            trace_id="trace-wp3-002",
        )
        resp = self.agent.handle(req)
        assert resp.intent_confirmed == IntentClass.QUERY
        assert resp.advisory_text
        assert resp.routing_suggestion is not None  # governance → suggests auditor

    def test_query_in_governance_includes_auditor_suggestion(self) -> None:
        req = SecretaryRequest(
            message="What is the current budget risk?",
            intent=IntentClass.QUERY,
            context=_ctx("governance"),
            trace_id="trace-wp3-003",
        )
        resp = self.agent.handle(req)
        # routing_suggestion for governance query should mention auditor
        assert resp.routing_suggestion is not None
        assert "auditor" in resp.routing_suggestion.lower()


# ---------------------------------------------------------------------------
# Advisory policy profile: mutation and admin are denied
# ---------------------------------------------------------------------------


class TestSecretaryAgentPolicyProfile:
    def setup_method(self) -> None:
        self.agent = _make_agent()

    def test_mutation_intent_raises_secretary_policy_error(self) -> None:
        req = SecretaryRequest(
            message="Pause project alpha",
            intent=IntentClass.MUTATION,
            context=_ctx("leadership_council"),
            trace_id="trace-wp3-004",
        )
        with pytest.raises(SecretaryPolicyError) as exc:
            self.agent.handle(req)
        assert exc.value.code == "secretary_advisory_policy_denied"
        assert "mutation" in exc.value.message.lower()

    def test_admin_intent_raises_secretary_policy_error(self) -> None:
        req = SecretaryRequest(
            message="/oq doctor",
            intent=IntentClass.ADMIN,
            context=_ctx("executive"),
            trace_id="trace-wp3-005",
        )
        with pytest.raises(SecretaryPolicyError) as exc:
            self.agent.handle(req)
        assert exc.value.code == "secretary_advisory_policy_denied"
        assert "admin" in exc.value.message.lower()


# ---------------------------------------------------------------------------
# Secretary memory and mention context (M17 fix)
# ---------------------------------------------------------------------------


class TestSecretaryConversationAndMentionContext:
    def test_channel_scoped_history_is_used_and_turn_is_persisted(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = _served_response("History-aware advisory")
        conversation_store = MagicMock()
        conversation_store.list_turns.return_value = (
            ConversationTurn(role="user", content="Previous user question"),
            ConversationTurn(role="assistant", content="Previous secretary answer"),
        )
        agent = SecretaryAgent(
            llm_gateway=cast(LlmGatewayService, llm),
            conversation_store=cast(ConversationStoreProtocol, conversation_store),
        )
        req = SecretaryRequest(
            message="What should we do next?",
            intent=IntentClass.QUERY,
            context=_ctx("governance"),
            trace_id="trace-m17-fix-001",
            channel_id="channel-123",
            guild_id="guild-123",
            actor_id="owner-123",
        )

        resp = agent.handle(req)

        assert resp.advisory_text == "History-aware advisory"
        conversation_store.list_turns.assert_called_once_with(
            "guild::guild-123::channel::channel-123"
        )
        conversation_store.append_turns.assert_called_once_with(
            "guild::guild-123::channel::channel-123",
            user_prompt="What should we do next?",
            assistant_reply="History-aware advisory",
        )
        sent_prompt = llm.complete.call_args.args[0].messages_or_prompt
        assert "Conversation so far:" in sent_prompt
        assert "User: Previous user question" in sent_prompt
        assert "Secretary: Previous secretary answer" in sent_prompt

    def test_addressed_agent_context_is_included_in_prompt(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = _served_response("Mention-aware advisory")
        agent = SecretaryAgent(llm_gateway=cast(LlmGatewayService, llm))
        req = SecretaryRequest(
            message="Can you help me run policy checks?",
            intent=IntentClass.DISCUSSION,
            context=_ctx("executive"),
            trace_id="trace-m17-fix-002",
            addressed_agent="administrator",
        )

        agent.handle(req)

        sent_prompt = llm.complete.call_args.args[0].messages_or_prompt
        assert "directed at the administrator agent" in sent_prompt
        assert "do NOT roleplay as or speak as the administrator" in sent_prompt


# ---------------------------------------------------------------------------
# Secretary NOT the default responder for project channels
# ---------------------------------------------------------------------------


class TestSecretaryNotActivatedInProjectChannels:
    def setup_method(self) -> None:
        self.router = FreeTextRouter()

    def test_discussion_in_project_channel_routes_to_project_manager_not_secretary(
        self,
    ) -> None:
        hint = self.router.resolve(IntentClass.DISCUSSION, _ctx("project", "proj-1"))
        assert hint.target_role == "project_manager"
        assert hint.target_role != "secretary"

    def test_query_in_project_channel_routes_to_project_manager_not_secretary(self) -> None:
        hint = self.router.resolve(IntentClass.QUERY, _ctx("project", "proj-2"))
        assert hint.target_role == "project_manager"
        assert hint.target_role != "secretary"


# ---------------------------------------------------------------------------
# Secretary channel membership activation (M11-WP3)
# ---------------------------------------------------------------------------


class TestSecretaryChannelMembership:
    def test_secretary_not_pending_activation(self) -> None:
        """Secretary must be removed from _PENDING_ROLE_FLAGS in M11."""
        assert "secretary" not in _PENDING_ROLE_FLAGS

    def test_secretary_active_in_leadership_council(self) -> None:
        assert "secretary" in _MEMBERSHIP_BY_CHAT_CLASS["leadership_council"]

    def test_secretary_active_in_governance(self) -> None:
        assert "secretary" in _MEMBERSHIP_BY_CHAT_CLASS["governance"]

    def test_secretary_active_in_executive(self) -> None:
        assert "secretary" in _MEMBERSHIP_BY_CHAT_CLASS["executive"]

    def test_secretary_not_in_project_channel_membership(self) -> None:
        """Secretary is NOT a default project channel participant."""
        assert "secretary" not in _MEMBERSHIP_BY_CHAT_CLASS["project"]
