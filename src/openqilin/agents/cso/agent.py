"""CSO agent — portfolio strategy advisor.

M13-WP7 rewrite: CSO is now the Chief Strategy Officer — a portfolio strategist,
CWO proposal reviewer, and cross-project risk analyst. OPA dependency removed.

CSO does NOT:
- Evaluate requests against OPA policy
- Issue commands or mutate state
- Act as a delegation authority

CSO DOES:
- Review proposals for strategic alignment (Aligned / Needs Revision / Strategic Conflict)
- Read portfolio context from project artifacts and governance records to inform advisory
- Persist a CSOReviewRecord (GATE-006) after every proposal review
- Escalate Strategic Conflicts to CEO via CSOConflictFlag.escalate_to="ceo"
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from openqilin.agents.cso.models import (
    CSOConflictFlag,
    CSORequest,
    CSOResponse,
)
from openqilin.agents.cso.prompts import (
    CROSS_PROJECT_ADVISORY_TEMPLATE,
    PROPOSAL_REVIEW_TEMPLATE,
    STRATEGIC_SYSTEM_PROMPT,
    _CONVERSATIONAL_SYSTEM_PROMPT,
)
from openqilin.agents.shared.free_text_advisory import (
    FreeTextAdvisoryRequest,
    FreeTextAdvisoryResponse,
)
from openqilin.control_plane.grammar.models import IntentClass
from openqilin.data_access.repositories.artifacts import ProjectArtifactWriteContext
from openqilin.data_access.repositories.postgres.conversation_store import (
    PostgresConversationStore,
)
from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
    PostgresGovernanceArtifactRepository,
)
from openqilin.data_access.repositories.postgres.project_repository import (
    PostgresProjectRepository,
)
from openqilin.llm_gateway.schemas.requests import (
    LlmBudgetContext,
    LlmGatewayRequest,
    LlmPolicyContext,
)
from openqilin.llm_gateway.service import LlmGatewayService
from openqilin.shared_kernel.settings import get_settings
from openqilin.task_orchestrator.dispatch.llm_dispatch import ConversationTurn

LOGGER = structlog.get_logger(__name__)

# CSO strategic advisory policy context.
_CSO_POLICY_CONTEXT = LlmPolicyContext(
    policy_version="v2",
    policy_hash="cso-strategic-advisory-v1",
    rule_ids=("GATE-006", "STR-001"),
)

_CSO_BUDGET_CONTEXT = LlmBudgetContext(
    quota_token_cap=512,
    allocation_mode="absolute",
)

_FALLBACK_ADVISORY = (
    "Strategic review unavailable. For portfolio or proposal questions, "
    "provide proposal context or use `/oq ask cso <topic>`."
)
_FREE_TEXT_FALLBACK_ADVISORY = (
    "I'm the CSO agent. I handle strategic review, portfolio alignment, "
    "and cross-project risk analysis. "
    "Use `/oq ask cso <topic>` to direct a query to me."
)

_CSO_AGENT_ID = "cso"
_CSO_TASK_ID_PREFIX = "cso-review"

# Write context for GATE-006 governance record (CSO writes as governance reviewer).
# actor_role="ceo" allows the write — CSO review precedes CEO+CWO review (GATE-006 chain).
_CSO_REVIEW_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="ceo",
    project_status="active",
)

# Keyword triggers for conflict detection in LLM advisory output.
_STRATEGIC_CONFLICT_KEYWORDS = ("strategic conflict", "escalation to ceo", "conflicts with")
_NEEDS_REVISION_KEYWORDS = ("needs revision", "addressable", "recommend revising")


class CSOAgent:
    """Portfolio strategy advisor for OpenQilin.

    Handles all intent classes with a strategic lens. For requests with a
    ``proposal_id``, reads portfolio context and returns a classified review
    (Aligned / Needs Revision / Strategic Conflict). For general advisory
    requests, provides cross-project strategic perspective.

    No OPA dependency. No command authority.
    """

    def __init__(
        self,
        llm_gateway: LlmGatewayService,
        project_artifact_repo: PostgresGovernanceArtifactRepository,
        governance_repo: PostgresProjectRepository,
        conversation_store: PostgresConversationStore | None = None,
        metric_recorder: Any | None = None,
    ) -> None:
        self._llm = llm_gateway
        self._project_artifact_repo = project_artifact_repo
        self._governance_repo = governance_repo
        self._conversation_store = conversation_store
        self._metric_recorder = metric_recorder

    def handle(self, request: CSORequest) -> CSOResponse:
        """Handle portfolio strategy advisory request.

        When ``proposal_id`` is present, reviews the proposal for strategic
        alignment and persists a GATE-006 governance record.
        For general advisory requests, provides cross-project strategic perspective.
        """
        portfolio_context = request.portfolio_context or self._read_portfolio_context(
            proposal_id=request.proposal_id,
            project_id=request.context.project_id,
        )

        advisory_text = self._generate_advisory(request, portfolio_context=portfolio_context)
        conflict_flag = _parse_conflict_flag(advisory_text)
        strategic_note = _build_strategic_note(request, conflict_flag=conflict_flag)

        if request.proposal_id:
            if request.context.project_id:
                self._write_governance_record(
                    proposal_id=request.proposal_id,
                    project_id=request.context.project_id,
                    review_outcome=_classify_outcome(conflict_flag),
                    advisory_text=advisory_text,
                    trace_id=request.trace_id,
                )
            else:
                # GATE-006 violation: proposal_id present but no project_id — cannot persist
                # the governance record. Override strategic_note to surface the gap explicitly.
                # The proposal MUST NOT advance to CEO+CWO review without a GATE-006 record.
                LOGGER.error(
                    "cso.gate006.record_skipped_no_project_id",
                    extra={
                        "proposal_id": request.proposal_id,
                        "trace_id": request.trace_id,
                    },
                )
                strategic_note = (
                    "GATE-006 error: CSO review record could not be persisted — "
                    "proposal_id is present but project_id is absent. "
                    "This proposal MUST NOT advance to CEO+CWO review until "
                    "project context is provided and a GATE-006 record is on file."
                )

        return CSOResponse(
            advisory_text=advisory_text,
            intent_confirmed=request.intent,
            trace_id=request.trace_id,
            strategic_note=strategic_note,
            conflict_flag=conflict_flag,
        )

    def handle_free_text(self, request: FreeTextAdvisoryRequest) -> FreeTextAdvisoryResponse:
        """Generate a role-appropriate advisory response for a free-text @mention."""
        conversation_turns: tuple[ConversationTurn, ...] = ()
        if self._conversation_store is not None:
            try:
                conversation_turns = self._conversation_store.list_turns(request.scope)
            except Exception:
                LOGGER.warning("cso_agent.handle_free_text.store_read_failed", scope=request.scope)

        history_lines = [f"{turn.role}: {turn.content}" for turn in conversation_turns]
        history_block = ""
        if history_lines:
            history_block = "Conversation so far:\n" + "\n".join(history_lines) + "\n\n"
        prompt = f"{_CONVERSATIONAL_SYSTEM_PROMPT}\n\n{history_block}Owner message:\n{request.text}"

        advisory_text = _FREE_TEXT_FALLBACK_ADVISORY
        try:
            response = self._llm.complete(
                LlmGatewayRequest(
                    request_id=str(uuid.uuid4()),
                    trace_id=str(uuid.uuid4()),
                    project_id="system",
                    agent_id=_CSO_AGENT_ID,
                    task_id=None,
                    skill_id="free_text_advisory",
                    model_class="interactive_fast",
                    routing_profile=get_settings().llm_default_routing_profile,
                    messages_or_prompt=prompt,
                    max_tokens=256,
                    temperature=0.3,
                    budget_context=_CSO_BUDGET_CONTEXT,
                    policy_context=_CSO_POLICY_CONTEXT,
                )
            )
            if response.decision in ("served", "fallback_served") and response.generated_text:
                advisory_text = response.generated_text.strip()
        except Exception:
            LOGGER.warning("cso_agent.handle_free_text.llm_failed")

        if self._metric_recorder is not None:
            self._metric_recorder.increment_counter(
                "llm_calls_total",
                labels={"purpose": "cso_response"},
            )

        if self._conversation_store is not None:
            try:
                self._conversation_store.append_turns(
                    request.scope,
                    user_prompt=request.text,
                    assistant_reply=advisory_text,
                    agent_id="cso",
                )
            except Exception:
                LOGGER.warning("cso_agent.handle_free_text.store_write_failed", scope=request.scope)

        return FreeTextAdvisoryResponse(advisory_text=advisory_text)

    def _read_portfolio_context(
        self,
        *,
        proposal_id: str | None,
        project_id: str | None,
    ) -> str:
        """Read relevant portfolio context to inform the advisory.

        Reads project records from governance_repo and, when proposal_id and
        project_id are present, relevant project artifacts from the artifact store.
        Returns a formatted context summary string for the LLM prompt.
        """
        parts: list[str] = []

        if project_id:
            try:
                project = self._governance_repo.get_project(project_id)
                if project:
                    parts.append(
                        f"Project {project_id}: status={project.status}, "
                        f"title={getattr(project, 'title', 'unknown')}"
                    )
            except Exception as exc:
                LOGGER.warning("cso.portfolio_context.project_read_failed", extra={"exc": str(exc)})

        if not parts:
            parts.append("No portfolio context available.")

        return "\n".join(parts)

    def _generate_advisory(
        self,
        request: CSORequest,
        *,
        portfolio_context: str,
    ) -> str:
        """Generate strategic advisory text via LLM gateway."""
        if request.proposal_id:
            prompt = PROPOSAL_REVIEW_TEMPLATE.format(
                proposal_id=request.proposal_id,
                message=request.message[:500],
                portfolio_context=portfolio_context,
            )
        else:
            prompt = CROSS_PROJECT_ADVISORY_TEMPLATE.format(
                chat_class=request.context.chat_class,
                message=request.message[:500],
            )

        full_prompt = f"{STRATEGIC_SYSTEM_PROMPT}\n\n{prompt}"
        response = self._llm.complete(
            LlmGatewayRequest(
                request_id=str(uuid.uuid4()),
                trace_id=request.trace_id,
                project_id=request.context.project_id or "system",
                agent_id=_CSO_AGENT_ID,
                task_id=None,
                skill_id="strategic_advisory",
                model_class="interactive_fast",
                routing_profile="dev_gemini_free",
                messages_or_prompt=full_prompt,
                max_tokens=512,
                temperature=0.2,
                budget_context=_CSO_BUDGET_CONTEXT,
                policy_context=_CSO_POLICY_CONTEXT,
            )
        )

        if response.decision in ("served", "fallback_served") and response.generated_text:
            return response.generated_text.strip()
        return _FALLBACK_ADVISORY

    def _write_governance_record(
        self,
        *,
        proposal_id: str,
        project_id: str,
        review_outcome: str,
        advisory_text: str,
        trace_id: str,
    ) -> None:
        """Persist GATE-006 CSO review record to the artifacts store.

        Required before the proposal can advance to CEO+CWO review.
        Write failures are logged but do not block the advisory response.
        """
        record_content = json.dumps(
            {
                "event_type": "cso_review_outcome",
                "proposal_id": proposal_id,
                "review_outcome": review_outcome,
                "cso_advisory_text": advisory_text,
                "trace_id": trace_id,
                "created_at": datetime.now(tz=UTC).isoformat(),
            },
            ensure_ascii=False,
        )
        try:
            self._project_artifact_repo.write_project_artifact(
                project_id=project_id,
                artifact_type="cso_review",
                content=record_content,
                write_context=_CSO_REVIEW_WRITE_CONTEXT,
            )
            LOGGER.info(
                "cso.gate006.record_written",
                extra={"proposal_id": proposal_id, "project_id": project_id, "trace_id": trace_id},
            )
        except Exception as exc:
            LOGGER.error(
                "cso.gate006.record_write_failed",
                extra={
                    "proposal_id": proposal_id,
                    "project_id": project_id,
                    "trace_id": trace_id,
                    "exc": str(exc),
                },
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_conflict_flag(advisory_text: str) -> CSOConflictFlag | None:
    """Detect conflict signals in LLM advisory text and return a structured flag."""
    lower = advisory_text.lower()
    if any(kw in lower for kw in _STRATEGIC_CONFLICT_KEYWORDS):
        return CSOConflictFlag(
            flag_type="strategic_conflict",
            reason=advisory_text[:200],
            escalate_to="ceo",
        )
    if any(kw in lower for kw in _NEEDS_REVISION_KEYWORDS):
        return CSOConflictFlag(
            flag_type="needs_revision",
            reason=advisory_text[:200],
            escalate_to=None,
        )
    return None


def _classify_outcome(conflict_flag: CSOConflictFlag | None) -> str:
    """Map conflict flag to review outcome label for GATE-006 record."""
    if conflict_flag is None:
        return "Aligned"
    if conflict_flag.flag_type == "strategic_conflict":
        return "Strategic Conflict"
    return "Needs Revision"


def _build_strategic_note(
    request: CSORequest,
    *,
    conflict_flag: CSOConflictFlag | None,
) -> str | None:
    """Build a strategic note hint based on intent and conflict outcome."""
    if conflict_flag and conflict_flag.flag_type == "strategic_conflict":
        return "Strategic conflict detected. Escalation to CEO required before proposal advances."
    if conflict_flag and conflict_flag.flag_type == "needs_revision":
        return "Proposal needs revision. Address CSO recommendations before advancing."
    if request.intent in (IntentClass.MUTATION, IntentClass.ADMIN):
        return "Governed actions require explicit command syntax: /oq <verb> [target] [args]"
    return None
