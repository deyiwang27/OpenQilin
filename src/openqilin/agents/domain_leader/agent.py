"""Domain Leader agent — backend-routed virtual agent scoped to project context.

DL is surfaced only through PM escalation. It does NOT:
  - Reply directly to the Discord channel (PM synthesises channel reply).
  - Issue commands to specialists (command: deny; all specialist interactions route through PM).
  - Accept requests without project_id (always project-scoped).

Escalation chain for material domain risk: specialist → domain_leader → project_manager → cwo → ceo.
DL escalates to PM (not directly to CWO).
"""

from __future__ import annotations

import uuid

from openqilin.agents.domain_leader.models import (
    DomainLeaderCommandDeniedError,
    DomainLeaderProjectContextError,
    DomainLeaderRequest,
    DomainLeaderResponse,
    SpecialistReviewOutcome,
    SpecialistReviewRequest,
)
from openqilin.agents.domain_leader.prompts import (
    CLARIFICATION_TEMPLATE,
    DOMAIN_SYSTEM_PROMPT,
    ESCALATION_ADVISORY_TEMPLATE,
    SPECIALIST_REVIEW_TEMPLATE,
)
from openqilin.llm_gateway.schemas.requests import (
    LlmBudgetContext,
    LlmGatewayRequest,
    LlmPolicyContext,
)
from openqilin.llm_gateway.service import LlmGatewayService

_DL_POLICY_CONTEXT = LlmPolicyContext(
    policy_version="v2",
    policy_hash="domain-leader-v1",
    rule_ids=("DL-001", "DL-002", "DL-003"),
)

_DL_BUDGET_CONTEXT = LlmBudgetContext(
    quota_token_cap=512,
    allocation_mode="absolute",
)

_FALLBACK_DOMAIN_ADVISORY = (
    "Domain assessment pending. Please resubmit with additional context "
    "or escalate to Project Manager for CWO review."
)


class DomainLeaderAgent:
    """Backend-routed Domain Leader virtual agent.

    Always requires ``project_id`` on all requests. Raises
    ``DomainLeaderProjectContextError`` if missing.

    ``command: deny`` — ``dispatch_command`` raises
    ``DomainLeaderCommandDeniedError`` unconditionally.
    """

    def __init__(self, llm_gateway: LlmGatewayService) -> None:
        self._llm = llm_gateway

    def handle_escalation(self, request: DomainLeaderRequest) -> DomainLeaderResponse:
        """Receive PM escalation; produce domain response.

        DL assesses the escalation and returns a ``DomainLeaderResponse``.
        The PM synthesises the channel reply — DL never writes directly to Discord.

        On material domain risk that cannot be resolved: ``domain_outcome`` is
        ``"domain_risk_escalation"`` and ``escalate_to`` is ``"project_manager"``.
        """
        self._require_project_context(request.project_id)

        prompt = ESCALATION_ADVISORY_TEMPLATE.format(
            project_id=request.project_id,
            requesting_agent=request.requesting_agent,
            task_id=request.task_id or "N/A",
            message=request.message[:1000],
        )
        text = self._call_llm(
            project_id=request.project_id,
            trace_id=request.trace_id,
            skill_id="escalation_advisory",
            prompt=f"{DOMAIN_SYSTEM_PROMPT}\n\n{prompt}",
        )

        outcome, escalate_to, rework = _parse_domain_outcome(text)
        return DomainLeaderResponse(
            advisory_text=text,
            domain_outcome=outcome,
            escalate_to=escalate_to,
            rework_recommendations=rework,
            trace_id=request.trace_id,
        )

    def review_specialist_output(
        self, review_request: SpecialistReviewRequest
    ) -> SpecialistReviewOutcome:
        """Assess specialist output for correctness and quality (review: allow authority).

        Returns a ``SpecialistReviewOutcome`` with ``outcome`` of ``"allow"``
        or ``"needs_rework"`` with specific rework recommendations.
        """
        self._require_project_context(review_request.project_id)

        prompt = SPECIALIST_REVIEW_TEMPLATE.format(
            project_id=review_request.project_id,
            task_id=review_request.task_id,
            specialist_output=review_request.specialist_output[:2000],
        )
        text = self._call_llm(
            project_id=review_request.project_id,
            trace_id=review_request.trace_id,
            skill_id="specialist_review",
            prompt=f"{DOMAIN_SYSTEM_PROMPT}\n\n{prompt}",
        )

        outcome, rework = _parse_review_outcome(text)
        return SpecialistReviewOutcome(
            outcome=outcome,
            rework_recommendations=rework,
            trace_id=review_request.trace_id,
        )

    def handle_clarification_request(
        self,
        *,
        specialist_id: str,
        question: str,
        task_id: str,
        project_id: str,
        trace_id: str,
    ) -> DomainLeaderResponse:
        """Respond to a specialist technical clarification request.

        DL spec §6: this path is active in MVP-v2.
        Response is returned to the specialist via PM synthesis — not direct.
        """
        self._require_project_context(project_id)

        prompt = CLARIFICATION_TEMPLATE.format(
            project_id=project_id,
            specialist_id=specialist_id,
            task_id=task_id,
            question=question[:1000],
        )
        text = self._call_llm(
            project_id=project_id,
            trace_id=trace_id,
            skill_id="specialist_clarification",
            prompt=f"{DOMAIN_SYSTEM_PROMPT}\n\n{prompt}",
        )

        return DomainLeaderResponse(
            advisory_text=text,
            domain_outcome="resolved",
            escalate_to=None,
            rework_recommendations=None,
            trace_id=trace_id,
        )

    def dispatch_command(self, specialist_id: str) -> None:
        """Always raises ``DomainLeaderCommandDeniedError``.

        DL has ``command: deny`` authority. Direct specialist commands must route
        through ProjectManager.
        """
        raise DomainLeaderCommandDeniedError(specialist_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _require_project_context(project_id: str | None) -> None:
        if not project_id:
            raise DomainLeaderProjectContextError()

    def _call_llm(
        self,
        *,
        project_id: str,
        trace_id: str,
        skill_id: str,
        prompt: str,
    ) -> str:
        response = self._llm.complete(
            LlmGatewayRequest(
                request_id=str(uuid.uuid4()),
                trace_id=trace_id,
                project_id=project_id,
                agent_id="domain_leader",
                task_id=None,
                skill_id=skill_id,
                model_class="interactive_fast",
                routing_profile="dev_gemini_free",
                messages_or_prompt=prompt,
                max_tokens=512,
                temperature=0.3,
                budget_context=_DL_BUDGET_CONTEXT,
                policy_context=_DL_POLICY_CONTEXT,
            )
        )

        if response.decision in ("served", "fallback_served") and response.generated_text:
            return response.generated_text.strip()
        return _FALLBACK_DOMAIN_ADVISORY


def _parse_domain_outcome(text: str) -> tuple[str, str | None, str | None]:
    """Parse LLM text into (domain_outcome, escalate_to, rework_recommendations)."""
    upper = text.upper()
    if "ESCALATE_TO_PM" in upper or "ESCALATE TO PM" in upper:
        return "domain_risk_escalation", "project_manager", None
    if "NEEDS_REWORK" in upper or "NEEDS REWORK" in upper:
        return "needs_rework", None, text
    return "resolved", None, None


def _parse_review_outcome(text: str) -> tuple[str, str | None]:
    """Parse LLM review text into (outcome, rework_recommendations)."""
    upper = text.upper()
    if "NEEDS_REWORK" in upper or "NEEDS REWORK" in upper:
        return "needs_rework", text
    return "allow", None
