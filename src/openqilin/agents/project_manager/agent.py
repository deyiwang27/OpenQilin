"""Project Manager agent implementation."""

from __future__ import annotations

import json
import uuid
from typing import Any, Callable

import structlog

from openqilin.agents.domain_leader.agent import DomainLeaderAgent
from openqilin.agents.domain_leader.models import DomainLeaderRequest
from openqilin.agents.project_manager.artifact_writer import (
    CONDITIONAL_WRITE_TYPES,
    PMProjectArtifactWriter,
)
from openqilin.agents.project_manager.models import (
    PMProjectContextError,
    PMWriteNotAllowedError,
    ProjectManagerRequest,
    ProjectManagerResponse,
)
from openqilin.agents.project_manager.prompts import (
    ADMIN_DOCUMENT_TEMPLATE,
    DISCUSSION_QUERY_TEMPLATE,
    MUTATION_DISPATCH_TEMPLATE,
    PM_SYSTEM_PROMPT,
)
from openqilin.agents.secretary.data_access import SecretaryDataAccessService
from openqilin.data_access.repositories.artifacts import (
    ProjectArtifactDocument,
    ProjectArtifactWriteContext,
)
from openqilin.llm_gateway.schemas.requests import (
    LlmBudgetContext,
    LlmGatewayRequest,
    LlmPolicyContext,
)
from openqilin.llm_gateway.service import LlmGatewayService
from openqilin.task_orchestrator.admission.envelope_validator import AdmissionEnvelope
from openqilin.task_orchestrator.services.task_service import TaskDispatchService

LOGGER = structlog.get_logger(__name__)

_PM_POLICY_CONTEXT = LlmPolicyContext(
    policy_version="v2",
    policy_hash="project-manager-v1",
    rule_ids=("AUTH-001", "AUTH-002", "ORCH-001", "ORCH-002"),
)
_PM_BUDGET_CONTEXT = LlmBudgetContext(
    quota_token_cap=512,
    allocation_mode="absolute",
)
_FALLBACK_STATUS_TEXT = (
    "Status: project context is incomplete. Halt further mutation, refresh governed "
    "artifacts, and resolve blockers before proceeding."
)
_FALLBACK_MUTATION_TEXT = (
    "Decision: execution stays project-bound. Dispatch the required specialist and "
    "record governed changes before continuing."
)
_FALLBACK_ADMIN_TEXT = (
    "Decision: controlled document update denied until both CEO and CWO approval "
    "evidence are present."
)


class ProjectManagerAgent:
    """Project Manager default handler for project channels."""

    def __init__(
        self,
        llm_gateway: LlmGatewayService,
        artifact_writer: PMProjectArtifactWriter,
        data_access: SecretaryDataAccessService,
        domain_leader_agent: DomainLeaderAgent,
        task_dispatch_service: TaskDispatchService,
        project_artifact_repo: Any,
        trace_id_factory: Callable[[], str] | None = None,
        metric_recorder: Any | None = None,
    ) -> None:
        self._llm = llm_gateway
        self._artifact_writer = artifact_writer
        self._data_access = data_access
        self._domain_leader_agent = domain_leader_agent
        self._task_dispatch_service = task_dispatch_service
        self._project_artifact_repo = project_artifact_repo
        self._trace_id_factory = trace_id_factory or (lambda: str(uuid.uuid4()))
        self._metric_recorder = metric_recorder

    def handle(self, request: ProjectManagerRequest) -> ProjectManagerResponse:
        self._require_project_id(request.project_id)
        intent = request.intent.strip().upper()

        if intent in {"DISCUSSION", "QUERY"}:
            return self._handle_status_or_decision(request)
        if intent == "MUTATION":
            return self._handle_task_mutation(request)
        if intent == "ADMIN":
            return self._handle_document_admin(request)
        raise PMProjectContextError(f"Unsupported Project Manager intent: {request.intent!r}")

    def _handle_status_or_decision(self, request: ProjectManagerRequest) -> ProjectManagerResponse:
        snapshot = self._data_access.get_project_snapshot(request.project_id)
        execution_plan = self._read_latest_artifact(request.project_id, "execution_plan")
        progress_report = self._read_latest_artifact(request.project_id, "progress_report")
        prompt = DISCUSSION_QUERY_TEMPLATE.format(
            project_id=request.project_id,
            project_state=_project_state_from_snapshot(snapshot, request.context),
            active_tasks=getattr(snapshot, "active_task_count", 0),
            blocked_tasks=getattr(snapshot, "blocked_task_count", 0),
            milestone_posture=_milestone_posture(snapshot, execution_plan, progress_report),
            budget_state=str(request.context.get("budget_state", "unknown")),
            latest_execution_plan=_artifact_summary(execution_plan),
            latest_progress_report=_artifact_summary(progress_report),
            message=request.message[:1000],
        )
        advisory_text = self._complete_prompt(
            project_id=request.project_id,
            trace_id=request.trace_id,
            skill_id="status_or_decision",
            prompt=prompt,
            fallback=_FALLBACK_STATUS_TEXT,
        )
        return ProjectManagerResponse(
            advisory_text=_ensure_directive_language(advisory_text, prefix="Status"),
            action_taken=(
                "project_decision_issued"
                if request.intent.strip().upper() == "QUERY"
                else "status_reported"
            ),
            routing_hint=None,
            artifact_updated=False,
            trace_id=request.trace_id,
        )

    def _handle_task_mutation(self, request: ProjectManagerRequest) -> ProjectManagerResponse:
        project_state = self._resolve_project_state(request)
        budget_state = str(request.context.get("budget_state", "unknown")).strip().lower()

        if budget_state in {"risk", "at_risk", "warning"}:
            self._emit_budget_risk_escalation(
                request.project_id,
                reason=str(request.context.get("budget_reason", request.message)),
                trace_id=request.trace_id,
            )

        artifact_updated = False
        action_taken: str | None = None
        routing_hint: str | None = None

        artifact_type = _optional_str(request.context.get("artifact_type"))
        content_md = _optional_str(request.context.get("content_md"))
        if artifact_type and content_md:
            self._artifact_writer.write(
                request.project_id,
                artifact_type,
                content_md,
                request.trace_id,
                project_state,
                approval_evidence=request.context.get("approval_evidence"),
            )
            artifact_updated = True
            action_taken = "artifact_written"

        task_id = _optional_str(request.context.get("task_id"))
        if task_id:
            self.dispatch_to_specialist(task_id, request.project_id, request.trace_id)
            action_taken = "specialist_dispatched"
            routing_hint = "specialist"

        prompt = MUTATION_DISPATCH_TEMPLATE.format(
            project_id=request.project_id,
            project_state=project_state,
            artifact_type=artifact_type or "none",
            task_id=task_id or "none",
            budget_state=budget_state or "unknown",
            message=request.message[:1000],
        )
        advisory_text = self._complete_prompt(
            project_id=request.project_id,
            trace_id=request.trace_id,
            skill_id="task_mutation",
            prompt=prompt,
            fallback=_FALLBACK_MUTATION_TEXT,
        )
        return ProjectManagerResponse(
            advisory_text=_ensure_directive_language(advisory_text, prefix="Decision"),
            action_taken=action_taken,
            routing_hint=routing_hint,
            artifact_updated=artifact_updated,
            trace_id=request.trace_id,
        )

    def _handle_document_admin(self, request: ProjectManagerRequest) -> ProjectManagerResponse:
        approval_evidence = self._resolve_approval_evidence(request)
        approval_roles = _normalize_approval_roles(approval_evidence)
        missing_roles = tuple(sorted({"ceo", "cwo"} - set(approval_roles)))
        if missing_roles:
            raise PMWriteNotAllowedError(
                "Controlled document update denied without CEO+CWO approval evidence: "
                + ", ".join(missing_roles)
            )

        artifact_type = _optional_str(request.context.get("artifact_type"))
        content_md = _optional_str(request.context.get("content_md"))
        if artifact_type is None or content_md is None:
            raise PMWriteNotAllowedError(
                "Controlled document update requires artifact_type and content_md"
            )
        if artifact_type not in CONDITIONAL_WRITE_TYPES:
            raise PMWriteNotAllowedError(
                f"ADMIN path only permits controlled artifact types, got: {artifact_type}"
            )

        self._artifact_writer.write(
            request.project_id,
            artifact_type,
            content_md,
            request.trace_id,
            self._resolve_project_state(request),
            approval_evidence=approval_evidence,
        )
        prompt = ADMIN_DOCUMENT_TEMPLATE.format(
            project_id=request.project_id,
            project_state=self._resolve_project_state(request),
            artifact_type=artifact_type,
            ceo_approval=str("ceo" in approval_roles).lower(),
            cwo_approval=str("cwo" in approval_roles).lower(),
            message=request.message[:1000],
        )
        advisory_text = self._complete_prompt(
            project_id=request.project_id,
            trace_id=request.trace_id,
            skill_id="document_admin",
            prompt=prompt,
            fallback=_FALLBACK_ADMIN_TEXT,
        )
        return ProjectManagerResponse(
            advisory_text=_ensure_directive_language(advisory_text, prefix="Decision"),
            action_taken="artifact_written",
            routing_hint=None,
            artifact_updated=True,
            trace_id=request.trace_id,
        )

    def dispatch_to_specialist(self, task_id: str, project_id: str, trace_id: str) -> str:
        source_task = self._load_task_record(task_id)
        if (
            source_task is None
            or _optional_str(getattr(source_task, "project_id", None)) != project_id
        ):
            raise PMProjectContextError(
                "AUTH-001 violated: Project Manager specialist dispatch must stay within project scope"
            )

        if hasattr(self._task_dispatch_service, "create_specialist_task"):
            created_task_id = str(
                self._task_dispatch_service.create_specialist_task(  # type: ignore[attr-defined]
                    task_id=task_id,
                    project_id=project_id,
                    trace_id=trace_id,
                )
            )
            return created_task_id

        # REVIEW_NOTE: M14-WP1 handoff requires PM dispatch via TaskDispatchService, but the current
        # runtime only exposes dispatch for already-admitted tasks. This implementation uses the
        # existing runtime-state repository behind TaskLifecycleService to create the project-bound
        # specialist task conservatively, then hands that admitted task to TaskDispatchService.
        runtime_state_repo = self._get_runtime_state_repo()
        if runtime_state_repo is None:
            raise RuntimeError(
                "Task dispatch runtime_state_repo is not available for specialist dispatch"
            )

        envelope = AdmissionEnvelope(
            request_id=self._trace_id_factory(),
            trace_id=trace_id,
            principal_id="project_manager",
            principal_role="project_manager",
            trust_domain="project",
            connector="internal",
            command="execute_specialist_task",
            target="specialist",
            args=(task_id,),
            metadata=(
                ("dispatch_source", "project_manager"),
                ("source_task_id", task_id),
                ("target_role", "specialist"),
            ),
            project_id=project_id,
            idempotency_key=f"pm-specialist-{project_id}-{task_id}-{trace_id}",
        )
        created_task = runtime_state_repo.create_task_from_envelope(envelope)
        self._task_dispatch_service.dispatch_admitted_task(
            created_task,
            policy_version="v2",
            policy_hash="project-manager-v1",
            rule_ids=("AUTH-001", "AUTH-002", "ORCH-001", "ORCH-002"),
        )
        return created_task.task_id

    def escalate_to_domain_leader(self, question: str, project_id: str, trace_id: str) -> str:
        response = self._domain_leader_agent.handle_escalation(
            DomainLeaderRequest(
                project_id=project_id,
                message=question,
                requesting_agent="project_manager",
                trace_id=trace_id,
            )
        )
        if response.domain_outcome == "domain_risk_escalation":
            return (
                "Domain Leader review found unresolved domain risk. Escalate through "
                "project governance to CWO before further execution."
            )
        if response.domain_outcome == "needs_rework":
            return (
                "Domain Leader review requires rework before execution continues. "
                "Update the task output and resubmit within the current project scope."
            )
        return (
            "Domain Leader review completed. The issue is resolved within project scope "
            "and execution may continue."
        )

    def _emit_budget_risk_escalation(self, project_id: str, reason: str, trace_id: str) -> None:
        if hasattr(self._project_artifact_repo, "write_escalation_event"):
            self._project_artifact_repo.write_escalation_event(  # type: ignore[attr-defined]
                project_id=project_id,
                escalation_type="budget_risk",
                source="project_manager",
                target="cwo",
                trace_id=trace_id,
                reason=reason,
                rule_ids=("ESC-004", "AUTH-002"),
            )
            return

        snapshot = self._data_access.get_project_snapshot(project_id)
        project_state = getattr(snapshot, "status", "unknown")
        if project_state != "active":
            LOGGER.warning(
                "pm.budget_risk_escalation_skipped_non_active",
                project_id=project_id,
                project_state=project_state,
                trace_id=trace_id,
            )
            return

        # REVIEW_NOTE: M14-WP1 does not inject a dedicated escalation event sink into
        # ProjectManagerAgent. Until governance/audit event wiring is added, persist the
        # PM -> CWO budget-risk escalation as a durable append-only decision_log record.
        self._project_artifact_repo.write_project_artifact(
            project_id=project_id,
            artifact_type="decision_log",
            content=json.dumps(
                {
                    "trace_id": trace_id,
                    "incident_type": "budget_risk",
                    "severity": "warning",
                    "current_owner_role": "project_manager",
                    "next_owner_role": "cwo",
                    "path_reference": "project_manager -> cwo",
                    "rule_ids": ["ESC-004", "AUTH-002"],
                    "message": reason,
                    "escalation_type": "budget_risk",
                    "source": "project_manager",
                    "target": "cwo",
                },
                sort_keys=True,
            ),
            write_context=ProjectArtifactWriteContext(
                actor_role="project_manager",
                project_status=project_state,
            ),
        )

    def _resolve_project_state(self, request: ProjectManagerRequest) -> str:
        context_state = _optional_str(request.context.get("project_state"))
        if context_state is not None:
            return context_state
        snapshot = self._data_access.get_project_snapshot(request.project_id)
        if snapshot is not None:
            return snapshot.status
        return "unknown"

    def _resolve_approval_evidence(self, request: ProjectManagerRequest) -> Any:
        if "approval_evidence" in request.context:
            return request.context["approval_evidence"]
        if hasattr(self._project_artifact_repo, "get_controlled_edit_approval_evidence"):
            return self._project_artifact_repo.get_controlled_edit_approval_evidence(  # type: ignore[attr-defined]
                project_id=request.project_id,
                artifact_type=request.context.get("artifact_type"),
            )
        return {}

    def _read_latest_artifact(
        self,
        project_id: str,
        artifact_type: str,
    ) -> ProjectArtifactDocument | None:
        if not hasattr(self._project_artifact_repo, "read_latest_artifact"):
            return None
        return self._project_artifact_repo.read_latest_artifact(
            project_id=project_id,
            artifact_type=artifact_type,
        )

    def _load_task_record(self, task_id: str) -> Any | None:
        task_context = self._data_access.get_task_runtime_context(task_id)
        if task_context is not None and hasattr(task_context, "project_id"):
            return task_context
        runtime_state_repo = getattr(self._data_access, "_runtime_state_repo", None)
        if runtime_state_repo is None:
            return None
        return runtime_state_repo.get_task_by_id(task_id)

    def _get_runtime_state_repo(self) -> Any | None:
        runtime_state_repo = getattr(self._task_dispatch_service, "_runtime_state_repo", None)
        if runtime_state_repo is not None:
            return runtime_state_repo
        lifecycle_service = getattr(self._task_dispatch_service, "_lifecycle_service", None)
        if lifecycle_service is None:
            return None
        return getattr(lifecycle_service, "_runtime_state_repo", None)

    def _complete_prompt(
        self,
        *,
        project_id: str,
        trace_id: str,
        skill_id: str,
        prompt: str,
        fallback: str,
    ) -> str:
        response = self._llm.complete(
            LlmGatewayRequest(
                request_id=self._trace_id_factory(),
                trace_id=trace_id,
                project_id=project_id,
                agent_id="project_manager",
                task_id=None,
                skill_id=skill_id,
                model_class="interactive_fast",
                routing_profile="dev_gemini_free",
                messages_or_prompt=f"{PM_SYSTEM_PROMPT}\n\n{prompt}",
                max_tokens=512,
                temperature=0.2,
                budget_context=_PM_BUDGET_CONTEXT,
                policy_context=_PM_POLICY_CONTEXT,
            )
        )
        if self._metric_recorder is not None:
            self._metric_recorder.increment_counter(
                "llm_calls_total",
                labels={"purpose": "pm_response"},
            )
        if response.decision in {"served", "fallback_served"} and response.generated_text:
            return response.generated_text.strip()
        return fallback

    @staticmethod
    def _require_project_id(project_id: str) -> None:
        if not project_id or not project_id.strip():
            raise PMProjectContextError()


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _project_state_from_snapshot(snapshot: Any, context: dict[str, Any]) -> str:
    context_state = _optional_str(context.get("project_state"))
    if context_state is not None:
        return context_state
    if snapshot is None:
        return "unknown"
    return str(getattr(snapshot, "status", "unknown"))


def _artifact_summary(document: ProjectArtifactDocument | None) -> str:
    if document is None:
        return "none"
    first_line = next(
        (line.strip() for line in document.content.splitlines() if line.strip()), "empty"
    )
    return f"v{document.pointer.revision_no}: {first_line[:160]}"


def _milestone_posture(
    snapshot: Any,
    execution_plan: ProjectArtifactDocument | None,
    progress_report: ProjectArtifactDocument | None,
) -> str:
    blocked_tasks = int(getattr(snapshot, "blocked_task_count", 0)) if snapshot is not None else 0
    if blocked_tasks > 0:
        return f"blocked:{blocked_tasks}"
    if progress_report is not None:
        return f"tracked_by_progress_report_v{progress_report.pointer.revision_no}"
    if execution_plan is not None:
        return f"tracked_by_execution_plan_v{execution_plan.pointer.revision_no}"
    return "not_reported"


def _normalize_approval_roles(approval_evidence: Any) -> tuple[str, ...]:
    if isinstance(approval_evidence, bool):
        return ("ceo", "cwo") if approval_evidence else ()
    if isinstance(approval_evidence, dict):
        if "approval_roles" in approval_evidence:
            raw_roles = approval_evidence.get("approval_roles")
            if isinstance(raw_roles, (list, tuple, set, frozenset)):
                return tuple(
                    sorted(str(role).strip().lower() for role in raw_roles if str(role).strip())
                )
        roles = []
        for role in ("ceo", "cwo"):
            if approval_evidence.get(role) or approval_evidence.get(f"{role}_approval"):
                roles.append(role)
        return tuple(sorted(roles))
    if isinstance(approval_evidence, (list, tuple, set, frozenset)):
        return tuple(
            sorted(str(role).strip().lower() for role in approval_evidence if str(role).strip())
        )
    return ()


def _ensure_directive_language(text: str, *, prefix: str) -> str:
    stripped = text.strip()
    lowered = stripped.lower()
    advisory_markers = ("i suggest", "you might consider", "consider ", "recommend ", "i recommend")
    if any(marker in lowered for marker in advisory_markers):
        return f"{prefix}: {stripped.replace('I suggest', 'Proceed with').replace('I recommend', 'Proceed with')}"
    if lowered.startswith(("status:", "decision:", "assignment:", "blocked:", "escalate:")):
        return stripped
    return f"{prefix}: {stripped}"
