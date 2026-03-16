"""Secretary agent — advisory-only institutional front-desk responder.

Policy profile: allow for advisory axis; deny for all mutation axes.
Secretary MUST NOT issue commands, mutate state, or act as delegation authority.
"""

from __future__ import annotations

import uuid

from openqilin.agents.secretary.models import (
    SecretaryPolicyError,
    SecretaryRequest,
    SecretaryResponse,
)
from openqilin.agents.secretary.prompts import (
    ADVISORY_SYSTEM_PROMPT,
    INTENT_DISAMBIGUATION_TEMPLATE,
    QUERY_ADVISORY_TEMPLATE,
)
from openqilin.control_plane.grammar.models import IntentClass
from openqilin.llm_gateway.schemas.requests import (
    LlmBudgetContext,
    LlmGatewayRequest,
    LlmPolicyContext,
)
from openqilin.llm_gateway.service import LlmGatewayService

# Secretary NEVER handles mutation or admin intents
_DENIED_INTENTS: frozenset[IntentClass] = frozenset({IntentClass.MUTATION, IntentClass.ADMIN})

_ADVISORY_POLICY_CONTEXT = LlmPolicyContext(
    policy_version="v2",
    policy_hash="secretary-advisory-v1",
    rule_ids=("advisory_only",),
)

_ADVISORY_BUDGET_CONTEXT = LlmBudgetContext(
    quota_token_cap=256,
    allocation_mode="absolute",
)

_FALLBACK_ADVISORY = (
    "I received your message. For specific actions, use `/oq <verb> [target] [args]`. "
    "For project questions, try `/oq ask project_manager <project> <question>`."
)


class SecretaryAgent:
    """Advisory-only front-desk agent for institutional channels.

    Handles discussion and query intents. Rejects mutation and admin intents
    at the advisory policy profile boundary before any LLM call.
    """

    def __init__(self, llm_gateway: LlmGatewayService) -> None:
        self._llm = llm_gateway

    def handle(self, request: SecretaryRequest) -> SecretaryResponse:
        """Handle advisory request. Raises SecretaryPolicyError for mutation/admin intents."""
        if request.intent in _DENIED_INTENTS:
            raise SecretaryPolicyError(
                code="secretary_advisory_policy_denied",
                message=(
                    f"Secretary advisory policy denies {request.intent.value} intent. "
                    "Use explicit command syntax for governed actions."
                ),
            )

        advisory_text = self._generate_advisory(request)
        routing_suggestion = _build_routing_suggestion(request)

        return SecretaryResponse(
            advisory_text=advisory_text,
            intent_confirmed=request.intent,
            routing_suggestion=routing_suggestion,
            trace_id=request.trace_id,
        )

    def _generate_advisory(self, request: SecretaryRequest) -> str:
        if request.intent == IntentClass.QUERY:
            prompt = QUERY_ADVISORY_TEMPLATE.format(
                chat_class=request.context.chat_class,
                message=request.message[:500],
            )
        else:
            prompt = INTENT_DISAMBIGUATION_TEMPLATE.format(
                chat_class=request.context.chat_class,
                message=request.message[:500],
            )

        full_prompt = f"{ADVISORY_SYSTEM_PROMPT}\n\n{prompt}"
        response = self._llm.complete(
            LlmGatewayRequest(
                request_id=str(uuid.uuid4()),
                trace_id=request.trace_id,
                project_id=request.context.project_id or "system",
                agent_id="secretary",
                task_id=None,
                skill_id="advisory_response",
                model_class="interactive_fast",
                routing_profile="dev_gemini_free",
                messages_or_prompt=full_prompt,
                max_tokens=256,
                temperature=0.3,
                budget_context=_ADVISORY_BUDGET_CONTEXT,
                policy_context=_ADVISORY_POLICY_CONTEXT,
            )
        )

        if response.decision in ("served", "fallback_served") and response.generated_text:
            return response.generated_text.strip()
        return _FALLBACK_ADVISORY


def _build_routing_suggestion(request: SecretaryRequest) -> str | None:
    """Build a routing suggestion hint based on chat class and intent."""
    if request.intent == IntentClass.QUERY:
        if request.context.chat_class == "governance":
            return "Try: /oq ask auditor <topic>"
        if request.context.chat_class == "executive":
            return "Try: /oq ask ceo <topic> or /oq ask cwo <topic>"
        return "Try: /oq status <project> or /oq ask <agent> <question>"
    return None
