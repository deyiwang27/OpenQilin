"""CSO agent — advisory governance gate for institutional channels.

Policy profile: governance-aware advisory; uses real OPA policy evaluation.
CSO MUST NOT issue commands, mutate state, or act as a delegation authority.
CSO activation requires a live OPAPolicyRuntimeClient — enforced at startup.
"""

from __future__ import annotations

import uuid

from openqilin.agents.cso.models import (
    CSOPolicyError,
    CSORequest,
    CSOResponse,
)
from openqilin.agents.cso.prompts import (
    GOVERNANCE_ADVISORY_TEMPLATE,
    GOVERNANCE_MUTATION_TEMPLATE,
    GOVERNANCE_SYSTEM_PROMPT,
)
from openqilin.control_plane.grammar.models import IntentClass
from openqilin.llm_gateway.schemas.requests import (
    LlmBudgetContext,
    LlmGatewayRequest,
    LlmPolicyContext,
)
from openqilin.llm_gateway.service import LlmGatewayService
from openqilin.policy_runtime_integration.client import PolicyRuntimeClient
from openqilin.policy_runtime_integration.models import PolicyEvaluationInput

# CSO advisory-only policy context: CSO itself is advisory — never mutation.
_CSO_POLICY_CONTEXT = LlmPolicyContext(
    policy_version="v2",
    policy_hash="cso-governance-advisory-v1",
    rule_ids=("advisory_governance",),
)

_CSO_BUDGET_CONTEXT = LlmBudgetContext(
    quota_token_cap=256,
    allocation_mode="absolute",
)

_FALLBACK_ADVISORY = (
    "I have reviewed your request. For governed actions, use explicit command syntax "
    "`/oq <verb> [target] [args]`. For policy clarification, try "
    "`/oq ask auditor <topic>`."
)

# Synthetic task ID for CSO advisory evaluations (not a real task).
_CSO_ADVISORY_TASK_ID = "cso-advisory-eval"
_CSO_ADVISORY_REQUEST_ID = "cso-advisory-eval"
_CSO_TRUST_DOMAIN = "institutional"
_CSO_CONNECTOR = "internal"


class CSOAgent:
    """Advisory governance gate for institutional channels.

    Handles all intent classes with a governance lens. For mutation and admin
    intents, evaluates the request against live OPA policy before generating
    an advisory response. For advisory and query intents, generates a
    governance-aware advisory directly.

    CSO MUST be activated only when a real OPAPolicyRuntimeClient is in use.
    Use assert_opa_client_required() to enforce this at startup.
    """

    def __init__(
        self,
        llm_gateway: LlmGatewayService,
        policy_client: PolicyRuntimeClient,
    ) -> None:
        self._llm = llm_gateway
        self._policy_client = policy_client

    def handle(self, request: CSORequest) -> CSOResponse:
        """Handle governance advisory request with OPA policy evaluation."""
        policy_decision: str | None = None

        if request.intent in (IntentClass.MUTATION, IntentClass.ADMIN):
            policy_result = self._evaluate_governance(request)
            policy_decision = policy_result.decision
            if policy_result.decision == "deny":
                rule_note = (
                    f" (rule: {', '.join(policy_result.rule_ids)})"
                    if policy_result.rule_ids
                    else ""
                )
                raise CSOPolicyError(
                    code="cso_governance_denied",
                    message=(
                        f"CSO governance gate: {request.intent.value} intent denied by policy"
                        f"{rule_note}. Use explicit command syntax for governed actions."
                    ),
                )

        advisory_text = self._generate_advisory(request, policy_decision=policy_decision)
        governance_note = self._build_governance_note(request, policy_decision=policy_decision)

        return CSOResponse(
            advisory_text=advisory_text,
            intent_confirmed=request.intent,
            governance_note=governance_note,
            trace_id=request.trace_id,
        )

    def _evaluate_governance(self, request: CSORequest) -> object:
        """Evaluate the request against OPA policy for governance gate decision."""
        policy_input = PolicyEvaluationInput(
            task_id=_CSO_ADVISORY_TASK_ID,
            request_id=_CSO_ADVISORY_REQUEST_ID,
            trace_id=request.trace_id,
            principal_id="cso-advisory-principal",
            principal_role=request.principal_role,
            trust_domain=_CSO_TRUST_DOMAIN,
            connector=_CSO_CONNECTOR,
            action=f"cso_advisory_{request.intent.value}",
            target="cso_governance_gate",
            recipient_types=(),
            recipient_ids=(),
            args=(),
            project_id=request.context.project_id,
        )
        return self._policy_client.evaluate(policy_input)

    def _generate_advisory(
        self,
        request: CSORequest,
        *,
        policy_decision: str | None,
    ) -> str:
        if request.intent in (IntentClass.MUTATION, IntentClass.ADMIN):
            prompt = GOVERNANCE_MUTATION_TEMPLATE.format(
                chat_class=request.context.chat_class,
                message=request.message[:500],
                principal_role=request.principal_role,
                policy_decision=policy_decision or "advisory",
            )
        else:
            prompt = GOVERNANCE_ADVISORY_TEMPLATE.format(
                chat_class=request.context.chat_class,
                message=request.message[:500],
                principal_role=request.principal_role,
            )

        full_prompt = f"{GOVERNANCE_SYSTEM_PROMPT}\n\n{prompt}"
        response = self._llm.complete(
            LlmGatewayRequest(
                request_id=str(uuid.uuid4()),
                trace_id=request.trace_id,
                project_id=request.context.project_id or "system",
                agent_id="cso",
                task_id=None,
                skill_id="governance_advisory",
                model_class="interactive_fast",
                routing_profile="dev_gemini_free",
                messages_or_prompt=full_prompt,
                max_tokens=256,
                temperature=0.2,
                budget_context=_CSO_BUDGET_CONTEXT,
                policy_context=_CSO_POLICY_CONTEXT,
            )
        )

        if response.decision in ("served", "fallback_served") and response.generated_text:
            return response.generated_text.strip()
        return _FALLBACK_ADVISORY

    def _build_governance_note(
        self,
        request: CSORequest,
        *,
        policy_decision: str | None,
    ) -> str | None:
        """Build a governance note hint based on intent and policy outcome."""
        if request.intent == IntentClass.MUTATION:
            return "Use explicit command syntax: /oq <verb> [target] [args]"
        if request.intent == IntentClass.ADMIN:
            return "Administrative actions require explicit governed commands and audit trail."
        if policy_decision == "allow_with_obligations":
            return "This action may require additional approval or obligation fulfilment."
        return None


def assert_opa_client_required(policy_client: PolicyRuntimeClient) -> None:
    """Raise RuntimeError if the CSO activation guard is not satisfied.

    CSO MUST NOT be activated without a real OPAPolicyRuntimeClient.
    This guard is called from build_runtime_services() before CSOAgent is instantiated.
    """
    from openqilin.policy_runtime_integration.client import OPAPolicyRuntimeClient

    if not isinstance(policy_client, OPAPolicyRuntimeClient):
        raise RuntimeError(
            "CSO must not be activated without real OPA client. "
            "Set OPENQILIN_OPA_URL to enable OPA and CSO activation."
        )
