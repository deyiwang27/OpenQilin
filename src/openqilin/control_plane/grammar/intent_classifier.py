"""Grammar layer intent classifier: classify Discord message into IntentClass."""

from __future__ import annotations

import time
import uuid
from typing import Any

from openqilin.control_plane.grammar.models import ChatContext, GrammarParseError, IntentClass
from openqilin.llm_gateway.schemas.requests import (
    LlmBudgetContext,
    LlmGatewayRequest,
    LlmPolicyContext,
)
from openqilin.llm_gateway.service import LlmGatewayService

_COMMAND_PREFIX = "/oq"

# Verb-to-intent mapping for explicit /oq commands
_MUTATION_VERBS: frozenset[str] = frozenset({"project", "escalate", "approve", "deny"})
_QUERY_VERBS: frozenset[str] = frozenset({"ask", "status"})
_ADMIN_VERBS: frozenset[str] = frozenset({"doctor", "discord", "governance"})

_CLASSIFICATION_PROMPT = """\
Classify the following owner message into exactly one intent class:
- discussion: open-ended conversation, planning, reasoning, exploration
- query: read-only information or status request
- mutation: explicit governed state change
- admin: operator-level system action

Respond with only one word (discussion, query, mutation, or admin). No punctuation.

Message:
{message}
"""

_INTENT_POLICY_CONTEXT = LlmPolicyContext(
    policy_version="v2",
    policy_hash="grammar-classifier-v1",
    rule_ids=("GRAM-003",),
)

_INTENT_BUDGET_CONTEXT = LlmBudgetContext(
    quota_token_cap=16,
    allocation_mode="absolute",
)


class IntentClassifier:
    """Classify inbound Discord messages into IntentClass before routing.

    For explicit /oq commands: derives intent from verb (no LLM call).
    For free text: calls LLM gateway with a lightweight classification prompt.
    Results are cached for 60 seconds per (message, channel_id) to avoid
    redundant LLM calls within a conversation window.
    Raises GrammarParseError(GRAM-004) if free-text mutation is detected.
    """

    _CACHE_TTL: float = 60.0

    def __init__(
        self,
        llm_gateway: LlmGatewayService,
        metric_recorder: Any | None = None,
    ) -> None:
        self._llm = llm_gateway
        self._metric_recorder = metric_recorder
        # (message[:1000], channel_id) -> (IntentClass, monotonic_timestamp)
        self._cache: dict[tuple[str, str], tuple[IntentClass, float]] = {}

    def classify(self, message: str, context: ChatContext) -> IntentClass:
        """Classify message intent. Raises GrammarParseError for free-text mutations."""
        stripped = message.strip()
        if stripped.startswith(_COMMAND_PREFIX):
            return _classify_command_intent(stripped)
        return self._classify_free_text(stripped, context)

    def _classify_free_text(self, message: str, context: ChatContext) -> IntentClass:
        cache_key = (message[:1000], context.channel_id)
        now = time.monotonic()
        cached = self._cache.get(cache_key)
        if cached is not None:
            result, ts = cached
            if now - ts < self._CACHE_TTL:
                return result  # cache hit - no LLM call, no metric increment

        # cache miss - call LLM
        prompt = _CLASSIFICATION_PROMPT.format(message=message[:1000])
        response = self._llm.complete(
            LlmGatewayRequest(
                request_id=str(uuid.uuid4()),
                trace_id=f"grammar-classify-{context.channel_id}",
                project_id=context.project_id or "system",
                agent_id="grammar_intent_classifier",
                task_id=None,
                skill_id="intent_classification",
                model_class="interactive_fast",
                routing_profile="dev_gemini_free",
                messages_or_prompt=prompt,
                max_tokens=16,
                temperature=0.0,
                budget_context=_INTENT_BUDGET_CONTEXT,
                policy_context=_INTENT_POLICY_CONTEXT,
            )
        )

        if response.decision not in ("served", "fallback_served"):
            # LLM unavailable - fail safe: treat unclassifiable as discussion.
            # Do NOT cache: fail-safe result should not mask future LLM recovery.
            return IntentClass.DISCUSSION

        raw = (response.generated_text or "").strip().lower()
        intent = _parse_intent_token(raw)

        if intent == IntentClass.MUTATION:
            # Raise before caching - mutation free-text is rejected, not stored.
            raise GrammarParseError(
                code="GRAM-004",
                message=(
                    "free-text input cannot be dispatched as a governed mutation. "
                    "Use explicit command syntax: /oq <verb> [target] [args]"
                ),
                details={"detected_intent": "mutation", "input_preview": message[:256]},
            )

        # Successful non-mutation classification: cache result, record metric.
        self._cache[cache_key] = (intent, now)
        if self._metric_recorder is not None:
            self._metric_recorder.increment_counter(
                "llm_calls_total",
                labels={"purpose": "intent_classification"},
            )

        return intent


def _classify_command_intent(message: str) -> IntentClass:
    """Derive intent from /oq verb without calling LLM."""
    tokens = message.split()
    if len(tokens) < 2:
        return IntentClass.ADMIN
    verb = tokens[1].lower()
    if verb in _MUTATION_VERBS:
        return IntentClass.MUTATION
    if verb in _QUERY_VERBS:
        return IntentClass.QUERY
    if verb in _ADMIN_VERBS:
        return IntentClass.ADMIN
    # Unknown command verb: default to MUTATION for fail-closed routing
    return IntentClass.MUTATION


def _parse_intent_token(raw: str) -> IntentClass:
    """Map LLM response text to IntentClass. Defaults to DISCUSSION on ambiguity."""
    for intent in IntentClass:
        if intent.value in raw:
            return intent
    return IntentClass.DISCUSSION
