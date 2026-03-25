"""CEO agent implementation."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Callable

import structlog

from openqilin.agents.ceo.decision_writer import CeoDecisionWriter
from openqilin.agents.ceo.models import (
    CeoCoApprovalError,
    CeoProposalGateError,
    CeoRequest,
    CeoResponse,
)
from openqilin.agents.ceo.prompts import (
    CEO_SYSTEM_PROMPT,
    CONTROLLED_DOC_TEMPLATE,
    PROPOSAL_REVIEW_TEMPLATE,
    STRATEGIC_DIRECTIVE_TEMPLATE,
    _CONVERSATIONAL_SYSTEM_PROMPT,
)
from openqilin.agents.cso.agent import CSOAgent
from openqilin.agents.shared.free_text_advisory import (
    FreeTextAdvisoryRequest,
    FreeTextAdvisoryResponse,
)
from openqilin.data_access.repositories.postgres.conversation_store import (
    PostgresConversationStore,
)
from openqilin.data_access.repositories.artifacts import ProjectArtifactDocument
from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
    PostgresGovernanceArtifactRepository,
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

_CEO_POLICY_CONTEXT = LlmPolicyContext(
    policy_version="v2",
    policy_hash="ceo-v1",
    rule_ids=("AUTH-001", "AUTH-002", "GOV-001", "ORCH-001", "ORCH-005"),
)
_CEO_BUDGET_CONTEXT = LlmBudgetContext(
    quota_token_cap=512,
    allocation_mode="absolute",
)
_FALLBACK_DIRECTIVE = (
    "Decision: hold execution at the current governance boundary until the required context and "
    "executive owner are confirmed."
)
_FALLBACK_PROPOSAL_REVIEW = (
    "Decision: needs_revision. Resolve the strategic and governance defects before resubmission."
)
_FALLBACK_COAPPROVAL = (
    "Decision: CEO co-approval recorded. Proceed only within governed change-control boundaries."
)
_FALLBACK_ADVISORY = (
    "I'm the CEO agent. I handle strategic directives, executive approvals, "
    "and co-approval of projects with the CWO. "
    "Use `/oq ask ceo <topic>` to direct a query to me."
)
_ADVISORY_MARKERS = (
    "i suggest",
    "you might consider",
    "consider ",
    "i recommend",
    "recommend ",
    "you may want to",
)
_WORKFORCE_KEYWORDS = (
    "workforce",
    "hiring",
    "hire",
    "staff",
    "staffing",
    "headcount",
    "recruit",
    "specialist assignment",
)
_STRATEGY_KEYWORDS = (
    "strategy",
    "strategic",
    "portfolio",
    "roadmap",
    "prioritization",
    "priority",
    "cross-project",
)
_OWNER_EXCEPTION_KEYWORDS = (
    "structural exception",
    "constitutional exception",
    "constitution",
    "structural",
    "owner decision",
    "owner override",
)
_PROJECT_EXECUTION_KEYWORDS = (
    "project execution",
    "milestone",
    "deliverable",
    "task execution",
    "execution blocker",
)


class CeoAgent:
    """Executive decision authority for proposals, directives, and co-approval."""

    def __init__(
        self,
        llm_gateway: LlmGatewayService,
        decision_writer: CeoDecisionWriter,
        governance_repo: PostgresGovernanceArtifactRepository,
        cso_agent: CSOAgent,
        trace_id_factory: Callable[[], str] | None = None,
        conversation_store: PostgresConversationStore | None = None,
        metric_recorder: Any | None = None,
    ) -> None:
        self._llm_gateway = llm_gateway
        self._decision_writer = decision_writer
        self._governance_repo = governance_repo
        self._cso_agent = cso_agent
        self._trace_id_factory = trace_id_factory or (lambda: str(uuid.uuid4()))
        self._conversation_store = conversation_store
        self._metric_recorder = metric_recorder

    def handle(self, request: CeoRequest) -> CeoResponse:
        intent = request.intent.strip().upper()
        if intent in {"DISCUSSION", "QUERY"}:
            return self._handle_directive(request)
        if intent == "MUTATION" and request.proposal_id:
            return self._handle_proposal_review(request)
        if intent == "MUTATION":
            return self._handle_executive_mutation(request)
        if intent == "ADMIN":
            return self._handle_coapproval(request)
        raise ValueError(f"Unsupported CEO intent: {request.intent!r}")

    def handle_free_text(self, request: FreeTextAdvisoryRequest) -> FreeTextAdvisoryResponse:
        """Generate a role-appropriate advisory response for a free-text @mention."""
        conversation_turns: tuple[ConversationTurn, ...] = ()
        if self._conversation_store is not None:
            try:
                conversation_turns = self._conversation_store.list_turns(request.scope)
            except Exception:
                LOGGER.warning("ceo_agent.handle_free_text.store_read_failed", scope=request.scope)

        history_lines = [f"{turn.role}: {turn.content}" for turn in conversation_turns]
        history_block = ""
        if history_lines:
            history_block = "Conversation so far:\n" + "\n".join(history_lines) + "\n\n"
        prompt = f"{_CONVERSATIONAL_SYSTEM_PROMPT}\n\n{history_block}Owner message:\n{request.text}"

        advisory_text = _FALLBACK_ADVISORY
        try:
            response = self._llm_gateway.complete(
                LlmGatewayRequest(
                    request_id=self._trace_id_factory(),
                    trace_id=self._trace_id_factory(),
                    project_id="system",
                    agent_id="ceo",
                    task_id=None,
                    skill_id="free_text_advisory",
                    model_class="interactive_fast",
                    routing_profile=get_settings().llm_default_routing_profile,
                    messages_or_prompt=prompt,
                    max_tokens=256,
                    temperature=0.3,
                    budget_context=_CEO_BUDGET_CONTEXT,
                    policy_context=_CEO_POLICY_CONTEXT,
                )
            )
            if response.decision in {"served", "fallback_served"} and response.generated_text:
                advisory_text = response.generated_text.strip()
        except Exception:
            LOGGER.warning("ceo_agent.handle_free_text.llm_failed")

        if self._metric_recorder is not None:
            self._metric_recorder.increment_counter(
                "llm_calls_total",
                labels={"purpose": "ceo_response"},
            )

        if self._conversation_store is not None:
            try:
                self._conversation_store.append_turns(
                    request.scope,
                    user_prompt=request.text,
                    assistant_reply=advisory_text,
                    agent_id="ceo",
                )
            except Exception:
                LOGGER.warning("ceo_agent.handle_free_text.store_write_failed", scope=request.scope)

        return FreeTextAdvisoryResponse(advisory_text=advisory_text)

    def _handle_directive(self, request: CeoRequest) -> CeoResponse:
        route = _classify_routing_hint(request)
        if route == "owner":
            return CeoResponse(
                decision=None,
                advisory_text=(
                    "Directive: structural or constitutional exception detected. Escalate to "
                    "owner for decision authority."
                ),
                routing_hint="owner",
                trace_id=request.trace_id,
            )
        if route == "cwo":
            return CeoResponse(
                decision=None,
                advisory_text=(
                    "Directive: workforce lifecycle matter detected. Route to CWO for execution "
                    "authority and governed handling."
                ),
                routing_hint="cwo",
                trace_id=request.trace_id,
            )
        if route == "cso":
            return CeoResponse(
                decision=None,
                advisory_text=(
                    "Directive: strategy question detected. Route to CSO for strategic review and "
                    "portfolio analysis."
                ),
                routing_hint="cso",
                trace_id=request.trace_id,
            )
        if route == "project_manager":
            return CeoResponse(
                decision=None,
                advisory_text=(
                    "Directive: project execution concern detected. Route to Project Manager for "
                    "operational handling."
                ),
                routing_hint="project_manager",
                trace_id=request.trace_id,
            )

        prompt = STRATEGIC_DIRECTIVE_TEMPLATE.format(
            intent=request.intent,
            message=request.message[:1000],
            context_summary=_context_summary(request.context),
        )
        directive = self._complete_llm(
            project_id=_optional_str(request.context.get("project_id")),
            trace_id=request.trace_id,
            prompt=prompt,
            fallback=_FALLBACK_DIRECTIVE,
        )
        return CeoResponse(
            decision=None,
            advisory_text=_ensure_executive_language(directive, prefix="Decision"),
            routing_hint=None,
            trace_id=request.trace_id,
        )

    def _handle_proposal_review(self, request: CeoRequest) -> CeoResponse:
        proposal_id = request.proposal_id
        if proposal_id is None or not proposal_id.strip():
            raise CeoProposalGateError("GATE-005 denied: proposal_id is required for CEO review")

        cso_record = self._verify_cso_review_record(proposal_id.strip())
        if cso_record is None:
            raise CeoProposalGateError("GATE-005 denied: no CSO review record")

        revision_cycle_count = self._read_revision_cycle_count(proposal_id.strip())
        override_flag = _coerce_bool(request.context.get("override_flag"))
        cso_review_outcome = request.cso_review_outcome or _optional_str(
            cso_record.get("review_outcome")
        )
        if (
            cso_review_outcome == "Strategic Conflict"
            and revision_cycle_count >= 3
            and not override_flag
        ):
            raise CeoProposalGateError(
                "GATE-003 denied: Strategic Conflict exceeded three unresolved revision cycles"
            )

        prompt = PROPOSAL_REVIEW_TEMPLATE.format(
            proposal_id=proposal_id,
            proposal_summary=request.message[:1500],
            cso_review_outcome=cso_review_outcome or "unknown",
            cso_advisory_text=_optional_str(cso_record.get("cso_advisory_text"))
            or "No CSO advisory text recorded.",
            revision_cycle_count=revision_cycle_count,
            project_scope=_optional_str(request.context.get("project_scope"))
            or _optional_str(request.context.get("scope"))
            or "unspecified",
        )
        llm_text = self._complete_llm(
            project_id=_optional_str(request.context.get("project_id")),
            trace_id=request.trace_id,
            prompt=prompt,
            fallback=_FALLBACK_PROPOSAL_REVIEW,
        )
        decision = _parse_proposal_decision(llm_text)
        rationale = llm_text.strip()
        self._decision_writer.write_proposal_decision(
            proposal_id=proposal_id,
            project_id=_optional_str(request.context.get("project_id")),
            decision=decision,
            rationale=rationale,
            cso_review_outcome=cso_review_outcome,
            revision_cycle_count=revision_cycle_count,
            override_flag=override_flag,
            trace_id=request.trace_id,
        )
        return CeoResponse(
            decision=decision,
            advisory_text=_ensure_executive_language(rationale, prefix="Decision"),
            routing_hint=None,
            trace_id=request.trace_id,
        )

    def _handle_executive_mutation(self, request: CeoRequest) -> CeoResponse:
        route = _classify_routing_hint(request)
        if route is not None:
            return self._handle_directive(request)
        mutation_text = self._complete_llm(
            project_id=_optional_str(request.context.get("project_id")),
            trace_id=request.trace_id,
            prompt=STRATEGIC_DIRECTIVE_TEMPLATE.format(
                intent=request.intent,
                message=request.message[:1000],
                context_summary=_context_summary(request.context),
            ),
            fallback=_FALLBACK_DIRECTIVE,
        )
        return CeoResponse(
            decision=None,
            advisory_text=_ensure_executive_language(mutation_text, prefix="Directive"),
            routing_hint=None,
            trace_id=request.trace_id,
        )

    def _handle_coapproval(self, request: CeoRequest) -> CeoResponse:
        project_id = _optional_str(request.context.get("project_id"))
        if project_id is None:
            raise CeoCoApprovalError("ORCH-005 denied: project_id is required for CEO co-approval")

        approval_type = _optional_str(request.context.get("approval_type")) or "controlled_doc_edit"
        artifact_type = _optional_str(request.context.get("artifact_type"))
        if not self._verify_cwo_coapproval(project_id, approval_type):
            raise CeoCoApprovalError(
                "ORCH-005 denied: missing CWO co-approval evidence for the requested action"
            )

        narrative = self._complete_llm(
            project_id=project_id,
            trace_id=request.trace_id,
            prompt=CONTROLLED_DOC_TEMPLATE.format(
                project_id=project_id,
                approval_type=approval_type,
                artifact_type=artifact_type or "none",
            ),
            fallback=_FALLBACK_COAPPROVAL,
        )
        self._decision_writer.write_coapproval_record(
            project_id=project_id,
            approval_type=approval_type,
            artifact_type=artifact_type,
            trace_id=request.trace_id,
        )
        return CeoResponse(
            decision="approved",
            advisory_text=_ensure_executive_language(narrative, prefix="Decision"),
            routing_hint=None,
            trace_id=request.trace_id,
        )

    def _verify_cso_review_record(self, proposal_id: str) -> dict[str, Any] | None:
        records = self._governance_repo.list_artifact_documents_by_type(artifact_type="cso_review")
        for document in reversed(records):
            payload = _load_record_payload(document)
            if payload.get("proposal_id") != proposal_id:
                continue
            event_type = _optional_str(payload.get("event_type"))
            if event_type in {None, "cso_review_outcome"}:
                return payload
        return None

    def _read_revision_cycle_count(self, proposal_id: str) -> int:
        count = 0
        for document in self._governance_repo.list_artifact_documents_by_type(
            artifact_type="cso_review"
        ):
            payload = _load_record_payload(document)
            if payload.get("proposal_id") == proposal_id and payload.get("review_outcome") == (
                "Strategic Conflict"
            ):
                count += 1
        for document in self._governance_repo.list_artifact_documents_by_type(
            artifact_type="ceo_proposal_decision"
        ):
            payload = _load_record_payload(document)
            if payload.get("proposal_id") == proposal_id and payload.get("decision") == (
                "needs_revision"
            ):
                count += 1
        return count

    def _verify_cwo_coapproval(self, project_id: str, approval_type: str) -> bool:
        for document in reversed(
            self._governance_repo.list_artifact_documents(
                project_id=project_id,
                artifact_type="cwo_coapproval",
            )
        ):
            payload = _load_record_payload(document)
            if payload.get("approval_type") == approval_type:
                return True
        return False

    def _complete_llm(
        self,
        *,
        project_id: str | None,
        trace_id: str,
        prompt: str,
        fallback: str,
    ) -> str:
        response = self._llm_gateway.complete(
            LlmGatewayRequest(
                request_id=self._trace_id_factory(),
                trace_id=trace_id,
                project_id=project_id or "system",
                agent_id="ceo",
                task_id=None,
                skill_id="executive_decision",
                model_class="interactive_fast",
                routing_profile="dev_gemini_free",
                messages_or_prompt=f"{CEO_SYSTEM_PROMPT}\n\n{prompt}",
                max_tokens=512,
                temperature=0.2,
                budget_context=_CEO_BUDGET_CONTEXT,
                policy_context=_CEO_POLICY_CONTEXT,
            )
        )
        if response.decision in {"served", "fallback_served"} and response.generated_text:
            return response.generated_text.strip()
        LOGGER.warning("ceo.llm.fallback", trace_id=trace_id, project_id=project_id)
        return fallback


def _classify_routing_hint(request: CeoRequest) -> str | None:
    message = " ".join(
        [
            request.message,
            _context_summary(request.context),
            _optional_str(request.context.get("topic")) or "",
        ]
    ).lower()
    if any(keyword in message for keyword in _OWNER_EXCEPTION_KEYWORDS):
        return "owner"
    if any(keyword in message for keyword in _WORKFORCE_KEYWORDS):
        return "cwo"
    if any(keyword in message for keyword in _STRATEGY_KEYWORDS):
        return "cso"
    if any(keyword in message for keyword in _PROJECT_EXECUTION_KEYWORDS):
        return "project_manager"
    return None


def _context_summary(context: dict[str, Any]) -> str:
    if not context:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(context.items()))


def _load_record_payload(document: ProjectArtifactDocument) -> dict[str, Any]:
    try:
        raw = json.loads(document.content)
    except json.JSONDecodeError:
        return {}
    if isinstance(raw, dict):
        return raw
    return {}


def _parse_proposal_decision(text: str) -> str:
    lowered = text.strip().lower()
    if re.search(r"\bneeds[_ -]?revision\b", lowered):
        return "needs_revision"
    if re.search(r"\bden(?:y|ied)\b", lowered):
        return "denied"
    if re.search(r"\bapprov(?:e|ed)\b", lowered):
        return "approved"
    return "needs_revision"


def _ensure_executive_language(text: str, *, prefix: str) -> str:
    stripped = text.strip()
    lowered = stripped.lower()
    for marker in _ADVISORY_MARKERS:
        lowered = lowered.replace(marker, "")
    replacements = {
        "I suggest": "Proceed",
        "I recommend": "Proceed",
        "You might consider": "Proceed",
        "Consider ": "Execute ",
        "consider ": "execute ",
    }
    normalized = stripped
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    if any(marker in stripped.lower() for marker in _ADVISORY_MARKERS):
        return f"{prefix}: {normalized}"
    if lowered.startswith(("decision:", "directive:", "route:", "approval:")):
        return stripped
    return f"{prefix}: {normalized}"


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}
