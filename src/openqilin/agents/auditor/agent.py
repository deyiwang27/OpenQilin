"""Auditor agent implementation."""

from __future__ import annotations

import json
import uuid
from typing import Any, Callable

import structlog

from openqilin.agents.auditor.enforcement import AuditWriter, AuditorEnforcementService
from openqilin.agents.auditor.models import AuditorRequest, AuditorResponse
from openqilin.agents.auditor.prompts import _CONVERSATIONAL_SYSTEM_PROMPT
from openqilin.agents.shared.free_text_advisory import (
    FreeTextAdvisoryRequest,
    FreeTextAdvisoryResponse,
)
from openqilin.data_access.repositories.artifacts import ProjectArtifactWriteContext
from openqilin.data_access.repositories.postgres.conversation_store import (
    PostgresConversationStore,
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

_AUDITOR_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="auditor",
    project_status="active",
)
_AUDITOR_POLICY_CONTEXT = LlmPolicyContext(
    policy_version="v2",
    policy_hash="auditor-advisory-v1",
    rule_ids=("GOV-001", "AUD-001"),
)
_AUDITOR_BUDGET_CONTEXT = LlmBudgetContext(
    quota_token_cap=256,
    allocation_mode="absolute",
)
_FALLBACK_ADVISORY = (
    "I'm the Auditor agent. I handle governance oversight, compliance monitoring, "
    "and escalation records. "
    "Use `/oq ask auditor <topic>` to direct a query to me."
)


class AuditorAgent:
    """Governance oversight agent that records findings and escalations."""

    def __init__(
        self,
        enforcement: AuditorEnforcementService,
        governance_repo: PostgresGovernanceArtifactRepository,
        audit_writer: AuditWriter,
        trace_id_factory: Callable[[], str] | None = None,
        llm_gateway: LlmGatewayService | None = None,
        conversation_store: PostgresConversationStore | None = None,
        metric_recorder: Any | None = None,
    ) -> None:
        self._enforcement = enforcement
        self._governance_repo = governance_repo
        self._audit_writer = audit_writer
        self._trace_id_factory = trace_id_factory or (lambda: str(uuid.uuid4()))
        self._llm_gateway = llm_gateway
        self._conversation_store = conversation_store
        self._metric_recorder = metric_recorder

    def handle(self, request: AuditorRequest) -> AuditorResponse:
        normalized_request = _normalize_request(request, trace_id_factory=self._trace_id_factory)
        event_type = normalized_request.event_type
        if event_type == "budget_breach":
            return self._handle_budget_breach(normalized_request)
        if event_type == "governance_violation":
            return self._handle_governance_violation(normalized_request)
        if event_type == "behavioral_violation":
            return self._handle_behavioral_violation(normalized_request)
        if event_type == "document_violation":
            return self._handle_document_violation(normalized_request)
        if event_type == "query":
            return self._handle_query(normalized_request)

        finding_id = self._enforcement.record_finding(
            project_id=normalized_request.project_id,
            finding_type=f"unknown_event_type:{event_type or 'unspecified'}",
            rule_ids=normalized_request.rule_ids,
            rationale=(
                f"Unsupported auditor event type received: {event_type or 'unspecified'}. "
                f"{normalized_request.rationale}"
            ).strip(),
            trace_id=normalized_request.trace_id,
            task_id=normalized_request.task_id,
            source_agent_role=normalized_request.source_agent_role,
            severity=normalized_request.severity,
        )
        return AuditorResponse(
            action_taken="finding_recorded",
            finding_id=finding_id,
            advisory_text=(
                "Oversight finding recorded for an unsupported event type. "
                f"Observed event_type={event_type or 'unspecified'}."
            ),
            trace_id=normalized_request.trace_id,
        )

    def handle_free_text(self, request: FreeTextAdvisoryRequest) -> FreeTextAdvisoryResponse:
        """Generate a role-appropriate advisory response for a free-text @mention."""
        conversation_turns: tuple[Any, ...] = ()
        if self._conversation_store is not None:
            try:
                conversation_turns = self._conversation_store.list_turns(request.scope)
            except Exception:
                LOGGER.warning(
                    "auditor_agent.handle_free_text.store_read_failed", scope=request.scope
                )

        history_lines = [f"{turn.role}: {turn.content}" for turn in conversation_turns]
        history_block = ""
        if history_lines:
            history_block = "Conversation so far:\n" + "\n".join(history_lines) + "\n\n"
        prompt = f"{_CONVERSATIONAL_SYSTEM_PROMPT}\n\n{history_block}Owner message:\n{request.text}"

        advisory_text = _FALLBACK_ADVISORY
        llm_attempted = False
        if self._llm_gateway is not None:
            llm_attempted = True
            try:
                response = self._llm_gateway.complete(
                    LlmGatewayRequest(
                        request_id=self._trace_id_factory(),
                        trace_id=self._trace_id_factory(),
                        project_id="system",
                        agent_id="auditor",
                        task_id=None,
                        skill_id="free_text_advisory",
                        model_class="interactive_fast",
                        routing_profile="dev_gemini_free",
                        messages_or_prompt=prompt,
                        max_tokens=256,
                        temperature=0.3,
                        budget_context=_AUDITOR_BUDGET_CONTEXT,
                        policy_context=_AUDITOR_POLICY_CONTEXT,
                    )
                )
                if response.decision in {"served", "fallback_served"} and response.generated_text:
                    advisory_text = response.generated_text.strip()
            except Exception:
                LOGGER.warning("auditor_agent.handle_free_text.llm_failed")

        if llm_attempted and self._metric_recorder is not None:
            self._metric_recorder.increment_counter(
                "llm_calls_total",
                labels={"purpose": "auditor_response"},
            )

        if self._conversation_store is not None:
            try:
                self._conversation_store.append_turns(
                    request.scope,
                    user_prompt=request.text,
                    assistant_reply=advisory_text,
                    agent_id="auditor",
                )
            except Exception:
                LOGGER.warning(
                    "auditor_agent.handle_free_text.store_write_failed", scope=request.scope
                )

        return FreeTextAdvisoryResponse(advisory_text=advisory_text)

    def _handle_budget_breach(self, request: AuditorRequest) -> AuditorResponse:
        if request.task_id:
            finding_id = self._enforcement.pause_task(
                request.task_id,
                project_id=request.project_id,
                reason=request.rationale,
                severity=request.severity,
                rule_ids=request.rule_ids,
                trace_id=request.trace_id,
            )
            self._enforcement.escalate_to_owner(
                project_id=request.project_id,
                rule_ids=request.rule_ids,
                rationale=request.rationale,
                severity=request.severity,
                trace_id=request.trace_id,
            )
            return AuditorResponse(
                action_taken="task_paused",
                finding_id=finding_id,
                advisory_text=(
                    "Oversight summary: hard budget breach recorded, task paused, and owner "
                    "escalation issued."
                ),
                trace_id=request.trace_id,
            )

        self._enforcement.escalate_to_owner(
            project_id=request.project_id,
            rule_ids=request.rule_ids,
            rationale=request.rationale,
            severity=request.severity,
            trace_id=request.trace_id,
        )
        finding_id = self._enforcement.record_finding(
            project_id=request.project_id,
            finding_type="budget_breach",
            rule_ids=request.rule_ids,
            rationale=request.rationale,
            trace_id=request.trace_id,
            task_id=request.task_id,
            source_agent_role=request.source_agent_role,
            severity=request.severity,
        )
        return AuditorResponse(
            action_taken="owner_escalated",
            finding_id=finding_id,
            advisory_text=(
                "Oversight summary: hard budget breach recorded and owner escalation issued."
            ),
            trace_id=request.trace_id,
        )

    def _handle_governance_violation(self, request: AuditorRequest) -> AuditorResponse:
        finding_id = self._enforcement.record_finding(
            project_id=request.project_id,
            finding_type="governance_violation",
            rule_ids=request.rule_ids,
            rationale=request.rationale,
            trace_id=request.trace_id,
            task_id=request.task_id,
            source_agent_role=request.source_agent_role,
            severity=request.severity,
        )
        self._enforcement.escalate_to_owner(
            project_id=request.project_id,
            rule_ids=request.rule_ids,
            rationale=request.rationale,
            severity=request.severity,
            trace_id=request.trace_id,
        )
        if request.severity in {"high", "critical"}:
            self._write_notification_artifact(
                project_id=request.project_id,
                artifact_type="auditor_ceo_notification",
                payload={
                    "event_type": "auditor_ceo_notification",
                    "author_role": "auditor",
                    "task_id": request.task_id,
                    "project_id": request.project_id,
                    "severity": request.severity,
                    "rule_ids": list(request.rule_ids),
                    "rationale": request.rationale,
                    "trace_id": request.trace_id,
                    "incident_type": "governance_violation",
                    "current_owner_role": "auditor",
                    "next_owner_role": "ceo",
                    "path_reference": "auditor->ceo",
                },
            )
        return AuditorResponse(
            action_taken="owner_escalated",
            finding_id=finding_id,
            advisory_text=(
                "Oversight summary: governance violation recorded and owner escalation issued."
            ),
            trace_id=request.trace_id,
        )

    def _handle_behavioral_violation(self, request: AuditorRequest) -> AuditorResponse:
        if self._finding_already_exists(
            request.project_id,
            request.task_id,
            request.source_agent_role,
        ):
            return AuditorResponse(
                action_taken="no_action",
                finding_id=None,
                advisory_text=(
                    "Oversight summary: matching behavioral finding already exists without new "
                    "evidence; duplicate escalation suppressed."
                ),
                trace_id=request.trace_id,
            )

        finding_id = self._enforcement.record_finding(
            project_id=request.project_id,
            finding_type="behavioral_violation",
            rule_ids=request.rule_ids,
            rationale=request.rationale,
            trace_id=request.trace_id,
            task_id=request.task_id,
            source_agent_role=request.source_agent_role,
            severity=request.severity,
        )
        self._enforcement.escalate_to_owner(
            project_id=request.project_id,
            rule_ids=request.rule_ids,
            rationale=request.rationale,
            severity=request.severity,
            trace_id=request.trace_id,
        )
        self._write_notification_artifact(
            project_id=request.project_id,
            artifact_type="auditor_ceo_notification",
            payload={
                "event_type": "auditor_ceo_notification",
                "author_role": "auditor",
                "task_id": request.task_id,
                "project_id": request.project_id,
                "severity": request.severity,
                "rule_ids": list(request.rule_ids),
                "rationale": request.rationale,
                "trace_id": request.trace_id,
                "incident_type": "behavioral_violation",
                "current_owner_role": "auditor",
                "next_owner_role": "ceo",
                "path_reference": "auditor->ceo",
                "source_agent_role": request.source_agent_role,
            },
        )
        return AuditorResponse(
            action_taken="owner_escalated",
            finding_id=finding_id,
            advisory_text=(
                "Oversight summary: behavioral violation recorded, bypass routing applied, and "
                "owner escalation issued."
            ),
            trace_id=request.trace_id,
        )

    def _handle_document_violation(self, request: AuditorRequest) -> AuditorResponse:
        finding_id = self._enforcement.record_finding(
            project_id=request.project_id,
            finding_type="document_violation",
            rule_ids=request.rule_ids,
            rationale=request.rationale,
            trace_id=request.trace_id,
            task_id=request.task_id,
            source_agent_role=request.source_agent_role,
            severity=request.severity,
        )
        self._enforcement.escalate_to_owner(
            project_id=request.project_id,
            rule_ids=request.rule_ids,
            rationale=request.rationale,
            severity=request.severity,
            trace_id=request.trace_id,
        )
        return AuditorResponse(
            action_taken="owner_escalated",
            finding_id=finding_id,
            advisory_text=(
                "Oversight summary: document-policy violation recorded and owner escalation issued."
            ),
            trace_id=request.trace_id,
        )

    def _handle_query(self, request: AuditorRequest) -> AuditorResponse:
        _ = self._audit_writer
        summary = (
            "Oversight summary: compliance query reviewed without new writes. "
            f"Severity={request.severity}; rules={', '.join(request.rule_ids) or 'none'}."
        )
        return AuditorResponse(
            action_taken="no_action",
            finding_id=None,
            advisory_text=summary,
            trace_id=request.trace_id,
        )

    def _finding_already_exists(
        self,
        project_id: str | None,
        task_id: str | None,
        source_agent_role: str | None,
    ) -> bool:
        if task_id is None or source_agent_role is None:
            return False
        for document in self._governance_repo.list_artifact_documents_by_type(
            artifact_type="auditor_finding"
        ):
            if project_id is not None and document.pointer.project_id != project_id:
                continue
            payload = _load_payload(document.content)
            if payload.get("task_id") != task_id:
                continue
            if payload.get("source_agent_role") != source_agent_role:
                continue
            if payload.get("finding_type") != "behavioral_violation":
                continue
            return True
        return False

    def _write_notification_artifact(
        self,
        *,
        project_id: str | None,
        artifact_type: str,
        payload: dict[str, object],
    ) -> str:
        durable_project_id = _require_project_scope(project_id, trace_id=str(payload["trace_id"]))
        pointer = self._governance_repo.write_project_artifact(
            project_id=durable_project_id,
            artifact_type=artifact_type,
            content=json.dumps(
                {
                    **payload,
                    "project_id": durable_project_id,
                },
                sort_keys=True,
            ),
            write_context=_AUDITOR_WRITE_CONTEXT,
        )
        return pointer.storage_uri


def _normalize_request(
    request: AuditorRequest,
    *,
    trace_id_factory: Callable[[], str],
) -> AuditorRequest:
    return AuditorRequest(
        event_type=request.event_type.strip().lower(),
        task_id=_normalize_optional_text(request.task_id),
        project_id=_normalize_optional_text(request.project_id),
        severity=_normalize_severity(request.severity),
        rule_ids=tuple(
            sorted({_normalize_rule_id(rule_id) for rule_id in request.rule_ids if rule_id})
        ),
        rationale=request.rationale.strip() or "No rationale provided.",
        source_agent_role=_normalize_optional_text(request.source_agent_role),
        trace_id=_normalize_optional_text(request.trace_id) or trace_id_factory(),
    )


def _normalize_rule_id(value: str) -> str:
    return value.strip()


def _normalize_severity(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"low", "medium", "high", "critical"}:
        return normalized
    return "high"


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _load_payload(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        LOGGER.warning("auditor.invalid_artifact_payload")
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _require_project_scope(project_id: str | None, *, trace_id: str) -> str:
    normalized_project_id = _normalize_optional_text(project_id)
    if normalized_project_id is None:
        raise ValueError(
            f"auditor notification requires project_id for durable scope (trace_id={trace_id})"
        )
    return normalized_project_id
