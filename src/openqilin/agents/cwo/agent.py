"""CWO agent implementation."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Callable

import structlog

from openqilin.agents.ceo.agent import CeoAgent
from openqilin.agents.ceo.models import CeoRequest
from openqilin.agents.cso.agent import CSOAgent
from openqilin.agents.cso.models import CSORequest
from openqilin.agents.cwo.models import (
    CwoCommandError,
    CwoRequest,
    CwoResponse,
)
from openqilin.agents.cwo.prompts import (
    CWO_SYSTEM_PROMPT,
    INITIALIZATION_COMPLETE_TEMPLATE,
    PROPOSAL_DRAFT_TEMPLATE,
    WORKFORCE_STATUS_TEMPLATE,
)
from openqilin.agents.cwo.workforce_initializer import WorkforceInitializer
from openqilin.agents.secretary.data_access import SecretaryDataAccessService
from openqilin.control_plane.grammar.models import ChatContext, IntentClass
from openqilin.data_access.repositories.artifacts import (
    ProjectArtifactDocument,
    ProjectArtifactWriteContext,
)
from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
    PostgresGovernanceArtifactRepository,
)
from openqilin.llm_gateway.schemas.requests import (
    LlmBudgetContext,
    LlmGatewayRequest,
    LlmPolicyContext,
)
from openqilin.llm_gateway.service import LlmGatewayService

LOGGER = structlog.get_logger(__name__)

_CWO_POLICY_CONTEXT = LlmPolicyContext(
    policy_version="v2",
    policy_hash="cwo-v1",
    rule_ids=("AUTH-001", "AUTH-002", "AUTH-003", "ORCH-001", "ORCH-002"),
)
_CWO_BUDGET_CONTEXT = LlmBudgetContext(
    quota_token_cap=512,
    allocation_mode="absolute",
)
_CWO_COAPPROVAL_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="cwo",
    project_status="active",
)
_FALLBACK_STATUS = (
    "Status: workforce posture is not ready for mutation. Refresh governed records and route "
    "unresolved blockers to the correct executive owner."
)
_FALLBACK_PROPOSAL = (
    "Command: draft the workforce package, submit it for CSO review, and hold activation until "
    "CEO and owner approvals are recorded."
)
_FALLBACK_INITIALIZATION = (
    "Command: workforce initialization recorded. Bind the approved template package and hold "
    "execution to the governed project scope."
)
_ADVISORY_MARKERS = (
    "i suggest",
    "you might consider",
    "consider ",
    "i recommend",
    "recommend ",
    "you may want to",
)
_STRATEGY_KEYWORDS = (
    "strategy",
    "strategic",
    "domain dispute",
    "portfolio conflict",
    "cross-project",
)
_EXECUTION_KEYWORDS = (
    "execution risk",
    "delivery blocker",
    "milestone blocker",
    "project execution",
    "implementation risk",
)
_BUDGET_KEYWORDS = (
    "budget blocker",
    "budget risk",
    "budget overrun",
    "policy blocker",
    "funding blocker",
)


class CwoAgent:
    """Workforce lifecycle authority for proposal flow and project readiness."""

    def __init__(
        self,
        llm_gateway: LlmGatewayService,
        cso_agent: CSOAgent,
        ceo_agent: CeoAgent,
        workforce_initializer: WorkforceInitializer,
        governance_repo: PostgresGovernanceArtifactRepository,
        data_access: SecretaryDataAccessService,
        trace_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._llm_gateway = llm_gateway
        self._cso_agent = cso_agent
        self._ceo_agent = ceo_agent
        self._workforce_initializer = workforce_initializer
        self._governance_repo = governance_repo
        self._data_access = data_access
        self._trace_id_factory = trace_id_factory or (lambda: str(uuid.uuid4()))

    def handle(self, request: CwoRequest) -> CwoResponse:
        intent = request.intent.strip().upper()
        action = _optional_str(request.context.get("action"))
        if intent in {"DISCUSSION", "QUERY"}:
            return self._handle_status(request)
        if intent == "MUTATION" and action == "submit_proposal":
            return self._handle_proposal_flow(request)
        if intent == "MUTATION" and action == "initialize_workforce":
            return self._handle_initialization(request)
        if intent == "ADMIN":
            return self._handle_coapproval(request)
        raise CwoCommandError(f"Unsupported CWO command action: {request.intent!r} / {action!r}")

    def _handle_status(self, request: CwoRequest) -> CwoResponse:
        route = _classify_routing_target(request)
        if route is not None:
            return CwoResponse(
                action_taken="routed",
                advisory_text=_route_text(route),
                workforce_status="blocked",
                trace_id=request.trace_id,
            )

        snapshot = (
            self._data_access.get_project_snapshot(request.project_id)
            if request.project_id
            else None
        )
        workforce_plan = self._artifact_summary(request.project_id, "workforce_plan")
        project_charter = self._artifact_summary(request.project_id, "project_charter")
        prompt = WORKFORCE_STATUS_TEMPLATE.format(
            project_id=request.project_id or "system",
            project_title=getattr(snapshot, "title", None) or "unknown",
            project_state=getattr(snapshot, "status", "unknown"),
            active_tasks=getattr(snapshot, "active_task_count", 0),
            blocked_tasks=getattr(snapshot, "blocked_task_count", 0),
            workforce_plan=workforce_plan,
            project_charter=project_charter,
            message=request.message[:1000],
        )
        status_text = self._complete_llm(
            project_id=request.project_id,
            trace_id=request.trace_id,
            prompt=prompt,
            fallback=_FALLBACK_STATUS,
        )
        return CwoResponse(
            action_taken=None,
            advisory_text=_ensure_command_language(status_text, prefix="Status"),
            workforce_status=_infer_workforce_status(snapshot, workforce_plan),
            trace_id=request.trace_id,
        )

    def _handle_proposal_flow(self, request: CwoRequest) -> CwoResponse:
        project_id = self._require_project_id(request.project_id, action="proposal submission")
        proposal_id = _optional_str(request.context.get("proposal_id")) or (
            f"{project_id}-{request.trace_id}"
        )
        project_scope = _optional_str(request.context.get("project_scope")) or request.message
        budget_context = _render_context_value(request.context.get("budget_context")) or "unknown"
        proposal_draft = self._complete_llm(
            project_id=project_id,
            trace_id=request.trace_id,
            prompt=PROPOSAL_DRAFT_TEMPLATE.format(
                project_id=project_id,
                project_scope=project_scope[:1500],
                budget_context=budget_context[:1000],
            ),
            fallback=_FALLBACK_PROPOSAL,
        )
        cso_response = self._cso_agent.handle(
            CSORequest(
                message=proposal_draft,
                intent=IntentClass.MUTATION,
                context=ChatContext(
                    chat_class="institutional",
                    channel_id="cwo",
                    project_id=project_id,
                ),
                trace_id=request.trace_id,
                proposal_id=proposal_id,
                portfolio_context=_optional_str(request.context.get("portfolio_context")),
            )
        )
        cso_review_outcome = self._read_cso_review_outcome(project_id, proposal_id)
        if cso_review_outcome is None:
            raise CwoCommandError(
                "GATE-006 denied: CSO review outcome record must exist before CEO review"
            )

        ceo_response = self._ceo_agent.handle(
            CeoRequest(
                message=proposal_draft,
                intent="MUTATION",
                context={
                    **request.context,
                    "project_id": project_id,
                    "project_scope": project_scope,
                    "cso_advisory_text": cso_response.advisory_text,
                },
                proposal_id=proposal_id,
                cso_review_outcome=cso_review_outcome,
                trace_id=request.trace_id,
            )
        )
        if ceo_response.decision == "approved":
            return CwoResponse(
                action_taken="proposal_submitted",
                advisory_text=_ensure_command_language(
                    "Workforce proposal submitted. CEO approved the package. Await owner "
                    f"co-approval before initialization. {ceo_response.advisory_text}",
                    prefix="Status",
                ),
                workforce_status="pending_owner_approval",
                trace_id=request.trace_id,
            )
        return CwoResponse(
            action_taken=None,
            advisory_text=_ensure_command_language(
                "Workforce proposal blocked. Hold initialization until the CEO decision path "
                f"is resolved. {ceo_response.advisory_text}",
                prefix="Status",
            ),
            workforce_status="blocked",
            trace_id=request.trace_id,
        )

    def _handle_initialization(self, request: CwoRequest) -> CwoResponse:
        project_id = self._require_project_id(request.project_id, action="workforce initialization")
        if not self._read_completion_report(project_id):
            raise CwoCommandError(
                "Workforce initialization denied: PM completion_report is required before "
                "CWO workforce-readiness authorization"
            )
        template = _required_context(request.context, "template")
        llm_profile = _required_context(request.context, "llm_profile")
        system_prompt_package = _required_context(request.context, "system_prompt_package")
        self._workforce_initializer.initialize(
            project_id=project_id,
            template=template,
            llm_profile=llm_profile,
            system_prompt_package=system_prompt_package,
            trace_id=request.trace_id,
        )
        self._write_cwo_coapproval(
            project_id=project_id,
            approval_type=_optional_str(request.context.get("approval_type"))
            or "project_completion",
            artifact_type=_optional_str(request.context.get("artifact_type")),
            trace_id=request.trace_id,
            project_state=_optional_str(request.context.get("project_state")) or "active",
        )
        completion_text = self._complete_llm(
            project_id=project_id,
            trace_id=request.trace_id,
            prompt=INITIALIZATION_COMPLETE_TEMPLATE.format(
                project_id=project_id,
                bound_template=template,
                bound_llm_profile=llm_profile,
            ),
            fallback=_FALLBACK_INITIALIZATION,
        )
        return CwoResponse(
            action_taken="workforce_initialized",
            advisory_text=_ensure_command_language(completion_text, prefix="Command"),
            workforce_status="initialized",
            trace_id=request.trace_id,
        )

    def _handle_coapproval(self, request: CwoRequest) -> CwoResponse:
        project_id = self._require_project_id(request.project_id, action="coapproval")
        approval_type = _optional_str(request.context.get("approval_type")) or "controlled_doc_edit"
        artifact_type = _optional_str(request.context.get("artifact_type"))
        if not self._has_ceo_coapproval(project_id, approval_type):
            raise CwoCommandError(
                "ORCH-005 denied: CEO co-approval evidence is required before CWO co-approval"
            )
        self._write_cwo_coapproval(
            project_id=project_id,
            approval_type=approval_type,
            artifact_type=artifact_type,
            trace_id=request.trace_id,
            project_state=_optional_str(request.context.get("project_state")) or "active",
        )
        return CwoResponse(
            action_taken="coapproval_recorded",
            advisory_text="Command: workforce readiness authorized within the controlled change scope.",
            workforce_status=None,
            trace_id=request.trace_id,
        )

    def _read_completion_report(self, project_id: str) -> bool:
        return (
            self._governance_repo.read_latest_artifact(
                project_id=project_id,
                artifact_type="completion_report",
            )
            is not None
        )

    def _artifact_summary(self, project_id: str | None, artifact_type: str) -> str:
        if project_id is None:
            return "none"
        document = self._governance_repo.read_latest_artifact(
            project_id=project_id,
            artifact_type=artifact_type,
        )
        if document is None:
            return "none"
        first_line = next(
            (line.strip() for line in document.content.splitlines() if line.strip()),
            "empty",
        )
        return first_line[:160]

    def _read_cso_review_outcome(self, project_id: str, proposal_id: str) -> str | None:
        for document in reversed(
            self._governance_repo.list_artifact_documents(
                project_id=project_id,
                artifact_type="cso_review",
            )
        ):
            payload = _load_record_payload(document)
            if payload.get("proposal_id") != proposal_id:
                continue
            event_type = _optional_str(payload.get("event_type"))
            if event_type not in {None, "cso_review_outcome"}:
                continue
            return _optional_str(payload.get("review_outcome"))
        return None

    def _has_ceo_coapproval(self, project_id: str, approval_type: str) -> bool:
        for document in reversed(
            self._governance_repo.list_artifact_documents(
                project_id=project_id,
                artifact_type="ceo_coapproval",
            )
        ):
            payload = _load_record_payload(document)
            if payload.get("approval_type") == approval_type:
                return True
        return False

    def _write_cwo_coapproval(
        self,
        *,
        project_id: str,
        approval_type: str,
        artifact_type: str | None,
        trace_id: str,
        project_state: str,
    ) -> None:
        self._governance_repo.write_project_artifact(
            project_id=project_id,
            artifact_type="cwo_coapproval",
            content=json.dumps(
                {
                    "event_type": "cwo_coapproval",
                    "approval_type": approval_type,
                    "artifact_type": artifact_type,
                    "trace_id": trace_id,
                    "author_role": "cwo",
                    "created_at": datetime.now(tz=UTC).isoformat(),
                },
                sort_keys=True,
            ),
            write_context=ProjectArtifactWriteContext(
                actor_role=_CWO_COAPPROVAL_WRITE_CONTEXT.actor_role,
                project_status=project_state,
            ),
        )

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
                agent_id="cwo",
                task_id=None,
                skill_id="workforce_command",
                model_class="interactive_fast",
                routing_profile="dev_gemini_free",
                messages_or_prompt=f"{CWO_SYSTEM_PROMPT}\n\n{prompt}",
                max_tokens=512,
                temperature=0.2,
                budget_context=_CWO_BUDGET_CONTEXT,
                policy_context=_CWO_POLICY_CONTEXT,
            )
        )
        if response.decision in {"served", "fallback_served"} and response.generated_text:
            return response.generated_text.strip()
        LOGGER.warning("cwo.llm.fallback", trace_id=trace_id, project_id=project_id)
        return fallback

    @staticmethod
    def _require_project_id(project_id: str | None, *, action: str) -> str:
        normalized = _optional_str(project_id)
        if normalized is None:
            raise CwoCommandError(f"CWO {action} requires a non-empty project_id")
        return normalized


def _load_record_payload(document: ProjectArtifactDocument) -> dict[str, Any]:
    try:
        raw = json.loads(document.content)
    except json.JSONDecodeError:
        return {}
    if isinstance(raw, dict):
        return raw
    return {}


def _classify_routing_target(request: CwoRequest) -> str | None:
    message = " ".join(
        [
            request.message,
            _context_summary(request.context),
            _optional_str(request.context.get("topic")) or "",
        ]
    ).lower()
    if any(keyword in message for keyword in _STRATEGY_KEYWORDS):
        return "cso"
    if any(keyword in message for keyword in _EXECUTION_KEYWORDS):
        return "project_manager"
    if any(keyword in message for keyword in _BUDGET_KEYWORDS):
        return "ceo"
    return None


def _route_text(route: str) -> str:
    if route == "cso":
        return "Command: route the domain strategy dispute to CSO for strategic review."
    if route == "project_manager":
        return (
            "Command: route the project execution risk to Project Manager for operational handling."
        )
    return "Command: route the budget or policy blocker to CEO for executive action."


def _infer_workforce_status(snapshot: object | None, workforce_plan: str) -> str | None:
    if workforce_plan != "none":
        return "initialized"
    status = _optional_str(getattr(snapshot, "status", None))
    if status in {"proposed", "approved"}:
        return "pending_approval"
    if status in {"blocked", "paused"}:
        return "blocked"
    return None


def _context_summary(context: dict[str, Any]) -> str:
    if not context:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(context.items()))


def _render_context_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _ensure_command_language(text: str, *, prefix: str) -> str:
    stripped = text.strip()
    lowered = stripped.lower()
    replacements = {
        "I suggest": "Execute",
        "I recommend": "Execute",
        "You might consider": "Execute",
        "Consider ": "Execute ",
        "consider ": "execute ",
    }
    normalized = stripped
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    if re.search(r"\bi approve\b", normalized, flags=re.IGNORECASE):
        normalized = re.sub(
            r"\bi approve\b",
            "CEO approval is recorded",
            normalized,
            flags=re.IGNORECASE,
        )
    if any(marker in lowered for marker in _ADVISORY_MARKERS):
        return f"{prefix}: {normalized}"
    if lowered.startswith(("status:", "command:", "route:", "directive:")):
        return normalized
    return f"{prefix}: {normalized}"


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_context(context: dict[str, Any], key: str) -> str:
    value = _optional_str(context.get(key))
    if value is None:
        raise CwoCommandError(f"CWO command requires context[{key!r}]")
    return value
