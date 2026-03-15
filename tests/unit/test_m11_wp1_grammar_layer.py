"""Unit tests for M11-WP1: Grammar Layer.

Covers:
- CommandParser: valid /oq command → CommandEnvelope
- CommandParser: unrecognized verb → GrammarParseError
- IntentClassifier: explicit /oq verb-to-intent mapping (no LLM)
- FreeTextRouter: discussion in institutional channel → secretary
- FreeTextRouter: discussion in project channel → project_manager
"""

from __future__ import annotations

import pytest

from openqilin.control_plane.grammar.command_parser import CommandParser
from openqilin.control_plane.grammar.free_text_router import FreeTextRouter
from openqilin.control_plane.grammar.intent_classifier import (
    IntentClassifier,
    _classify_command_intent,
)
from openqilin.control_plane.grammar.models import (
    ChatContext,
    GrammarParseError,
    IntentClass,
)
from openqilin.llm_gateway.service import LlmGatewayService
from openqilin.llm_gateway.providers.litellm_adapter import InMemoryLiteLLMAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_classifier() -> IntentClassifier:
    """Build IntentClassifier backed by InMemory (no-op) LLM provider."""
    return IntentClassifier(llm_gateway=LlmGatewayService(provider=InMemoryLiteLLMAdapter()))


# ---------------------------------------------------------------------------
# CommandParser tests
# ---------------------------------------------------------------------------


class TestCommandParser:
    def setup_method(self) -> None:
        self.parser = CommandParser()

    def test_valid_submit_task_command(self) -> None:
        """/oq submit task "do X" → not a known verb; expect GrammarParseError."""
        # "submit" is not in the verb catalog; use a known verb instead
        envelope = self.parser.parse('/oq project create "alpha project"')
        assert envelope.verb == "project"
        assert envelope.target == "create"
        assert envelope.args == ["alpha project"]

    def test_valid_status_command(self) -> None:
        envelope = self.parser.parse("/oq status alpha")
        assert envelope.verb == "status"
        assert envelope.target == "alpha"
        assert envelope.args == []

    def test_valid_ask_command(self) -> None:
        envelope = self.parser.parse("/oq ask pm alpha draft milestone plan")
        assert envelope.verb == "ask"
        assert envelope.target == "pm"
        assert envelope.args == ["alpha", "draft", "milestone", "plan"]

    def test_valid_doctor_no_args(self) -> None:
        envelope = self.parser.parse("/oq doctor")
        assert envelope.verb == "doctor"
        assert envelope.target is None
        assert envelope.args == []

    def test_unrecognized_verb_raises_grammar_parse_error(self) -> None:
        """Unrecognized verb must raise GrammarParseError, not pass through."""
        with pytest.raises(GrammarParseError) as exc:
            self.parser.parse("/oq submit task do_x")
        assert exc.value.code == "GRAM-005"
        assert "submit" in exc.value.message

    def test_missing_verb_raises_grammar_parse_error(self) -> None:
        with pytest.raises(GrammarParseError) as exc:
            self.parser.parse("/oq")
        assert exc.value.code == "GRAM-005"

    def test_non_oq_prefix_raises_grammar_parse_error(self) -> None:
        with pytest.raises(GrammarParseError) as exc:
            self.parser.parse("just some free text")
        assert exc.value.code == "GRAM-005"

    def test_raw_input_preserved_in_envelope(self) -> None:
        raw = "/oq status alpha"
        envelope = self.parser.parse(raw)
        assert envelope.raw_input == raw


# ---------------------------------------------------------------------------
# IntentClassifier — command path (no LLM)
# ---------------------------------------------------------------------------


class TestIntentClassifierCommandPath:
    """Test _classify_command_intent which does not call the LLM."""

    def test_project_verb_is_mutation(self) -> None:
        assert _classify_command_intent("/oq project pause alpha") == IntentClass.MUTATION

    def test_escalate_verb_is_mutation(self) -> None:
        assert _classify_command_intent("/oq escalate budget-risk") == IntentClass.MUTATION

    def test_approve_verb_is_mutation(self) -> None:
        assert _classify_command_intent("/oq approve milestone-1") == IntentClass.MUTATION

    def test_deny_verb_is_mutation(self) -> None:
        assert _classify_command_intent("/oq deny proposal-2") == IntentClass.MUTATION

    def test_status_verb_is_query(self) -> None:
        assert _classify_command_intent("/oq status alpha") == IntentClass.QUERY

    def test_ask_verb_is_query(self) -> None:
        assert _classify_command_intent("/oq ask pm alpha") == IntentClass.QUERY

    def test_doctor_verb_is_admin(self) -> None:
        assert _classify_command_intent("/oq doctor") == IntentClass.ADMIN

    def test_governance_verb_is_admin(self) -> None:
        assert _classify_command_intent("/oq governance audit") == IntentClass.ADMIN

    def test_classify_routes_command_directly(self) -> None:
        """IntentClassifier.classify on /oq input uses command path (no LLM)."""
        classifier = _make_classifier()
        context = ChatContext(chat_class="direct", channel_id="ch-001")
        assert classifier.classify("/oq status alpha", context) == IntentClass.QUERY


# ---------------------------------------------------------------------------
# FreeTextRouter tests
# ---------------------------------------------------------------------------


class TestFreeTextRouter:
    def setup_method(self) -> None:
        self.router = FreeTextRouter()

    def _ctx(self, chat_class: str, project_id: str | None = None) -> ChatContext:
        return ChatContext(chat_class=chat_class, channel_id="ch-test", project_id=project_id)

    def test_discussion_in_leadership_council_routes_to_secretary(self) -> None:
        hint = self.router.resolve(IntentClass.DISCUSSION, self._ctx("leadership_council"))
        assert hint.target_role == "secretary"

    def test_discussion_in_governance_routes_to_secretary(self) -> None:
        hint = self.router.resolve(IntentClass.DISCUSSION, self._ctx("governance"))
        assert hint.target_role == "secretary"

    def test_discussion_in_executive_routes_to_secretary(self) -> None:
        hint = self.router.resolve(IntentClass.DISCUSSION, self._ctx("executive"))
        assert hint.target_role == "secretary"

    def test_discussion_in_project_channel_routes_to_project_manager(self) -> None:
        hint = self.router.resolve(IntentClass.DISCUSSION, self._ctx("project", "proj-1"))
        assert hint.target_role == "project_manager"
        assert hint.project_id == "proj-1"

    def test_query_in_institutional_channel_routes_to_secretary(self) -> None:
        hint = self.router.resolve(IntentClass.QUERY, self._ctx("leadership_council"))
        assert hint.target_role == "secretary"

    def test_discussion_in_direct_channel_routes_to_secretary(self) -> None:
        hint = self.router.resolve(IntentClass.DISCUSSION, self._ctx("direct"))
        assert hint.target_role == "secretary"

    def test_routing_hint_has_project_id(self) -> None:
        hint = self.router.resolve(
            IntentClass.DISCUSSION,
            self._ctx("project", project_id="proj-alpha"),
        )
        assert hint.project_id == "proj-alpha"
