"""LangGraph node functions for the OpenQilin task orchestration graph."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from openqilin.observability.tracing.spans import (
    AUDIT_EMIT_SPAN,
    EXECUTION_SANDBOX_SPAN,
    POLICY_EVALUATION_SPAN,
)
from openqilin.policy_runtime_integration.fail_closed import evaluate_with_fail_closed
from openqilin.policy_runtime_integration.models import PolicyEvaluationInput
from openqilin.policy_runtime_integration.obligations import ObligationContext, ObligationDispatcher
from openqilin.task_orchestrator.loop_control import check_and_increment_hop
from openqilin.task_orchestrator.workflow.state_models import TaskState, WorkflowServices

if TYPE_CHECKING:
    pass


def _normalize_policy_input(task_id: str, services: WorkflowServices) -> PolicyEvaluationInput:
    from openqilin.policy_runtime_integration.normalizer import normalize_policy_input

    task = services.runtime_state_repo.get_task_by_id(task_id)
    if task is None:
        raise RuntimeError(f"task {task_id!r} not found in runtime_state_repo")
    return normalize_policy_input(task)


def _emit_stage_audit(
    *,
    services: WorkflowServices,
    task_id: str,
    trace_id: str,
    request_id: str,
    principal_id: str,
    principal_role: str,
    stage: str,
    decision: str,
    source: str,
    reason_code: str | None,
    message: str,
    policy_version: str | None = None,
    policy_hash: str | None = None,
    rule_ids: tuple[str, ...] = (),
) -> None:
    with services.tracer.start_span(
        trace_id=trace_id,
        name=AUDIT_EMIT_SPAN,
        attributes={"audit.event_type": f"{stage}.decision", "stage": stage},
    ) as span:
        span.set_attribute("correlation.task_id", task_id)
        span.set_attribute("decision", decision)
        services.audit_writer.write_event(
            event_type=f"{stage}.decision",
            outcome=decision,
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            principal_id=principal_id,
            principal_role=principal_role,
            source=source,
            reason_code=reason_code,
            message=message,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=list(rule_ids),
            payload={
                "stage": stage,
                "decision": decision,
                "source": source,
                "reason_code": reason_code,
            },
            attributes={
                "policy_version": policy_version,
                "policy_hash": policy_hash,
                "rule_ids": ",".join(rule_ids),
            },
        )


def _emit_outcome_audit(
    *,
    services: WorkflowServices,
    task_id: str,
    trace_id: str,
    request_id: str | None,
    principal_id: str | None,
    principal_role: str | None,
    outcome: str,
    error_code: str | None,
    message: str,
    source: str,
    policy_version: str | None = None,
    policy_hash: str | None = None,
    rule_ids: tuple[str, ...] = (),
    attributes: dict[str, object] | None = None,
) -> None:
    services.metric_recorder.increment_counter(
        "owner_command_admission_outcomes_total",
        labels={"outcome": outcome, "source": source},
    )
    with services.tracer.start_span(
        trace_id=trace_id,
        name=AUDIT_EMIT_SPAN,
        attributes={"audit.event_type": f"owner_command.{outcome}", "source": source},
    ) as span:
        span.set_attribute("correlation.trace_id", trace_id)
        span.set_attribute("outcome", outcome)
        services.audit_writer.write_event(
            event_type=f"owner_command.{outcome}",
            outcome=outcome,
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            principal_id=principal_id,
            principal_role=principal_role,
            source=source,
            reason_code=error_code,
            message=message,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=list(rule_ids),
            payload={
                "outcome": outcome,
                "source": source,
                "error_code": error_code,
                "message": message,
                "request_id": request_id,
                "task_id": task_id,
            },
            attributes=attributes,
        )


def make_policy_evaluation_node(services: WorkflowServices) -> Any:
    def policy_evaluation_node(state: TaskState) -> dict[str, Any]:
        check_and_increment_hop(state["loop_state"])
        task_id = state["task_id"]
        task = services.runtime_state_repo.get_task_by_id(task_id)
        if task is None:
            return {
                "policy_decision": "error",
                "policy_version": "policy-version-unknown",
                "policy_hash": "policy-hash-unknown",
                "rule_ids": (),
                "final_state": "failed",
            }
        policy_input = _normalize_policy_input(task_id, services)
        with services.tracer.start_span(
            trace_id=task.trace_id,
            name=POLICY_EVALUATION_SPAN,
            attributes={"stage": "policy_evaluation"},
        ) as policy_span:
            policy_span.set_attribute("correlation.task_id", task_id)
            policy_outcome = evaluate_with_fail_closed(policy_input, services.policy_runtime_client)
        policy_decision = (
            policy_outcome.policy_result.decision if policy_outcome.policy_result else "error"
        )
        policy_version = (
            policy_outcome.policy_result.policy_version
            if policy_outcome.policy_result
            else "policy-version-unknown"
        )
        policy_hash = (
            policy_outcome.policy_result.policy_hash
            if policy_outcome.policy_result
            else "policy-hash-unknown"
        )
        rule_ids = (
            tuple(policy_outcome.policy_result.rule_ids) if policy_outcome.policy_result else ()
        )
        reason_code = (
            policy_outcome.policy_result.reason_code
            if policy_outcome.policy_result
            else policy_outcome.error_code
        )
        _emit_stage_audit(
            services=services,
            task_id=task_id,
            trace_id=task.trace_id,
            request_id=task.request_id,
            principal_id=task.principal_id,
            principal_role=task.principal_role,
            stage="policy",
            decision=policy_decision,
            source="policy_runtime",
            reason_code=reason_code,
            message=policy_outcome.message,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
        )
        if not policy_outcome.allowed:
            services.runtime_state_repo.update_task_status(
                task_id,
                "blocked",
                outcome_source="policy_runtime",
                outcome_error_code=policy_outcome.error_code or "policy_blocked",
                outcome_message=policy_outcome.message,
                outcome_details={
                    "decision": policy_decision,
                    "policy_version": policy_version,
                    "policy_hash": policy_hash,
                    "rule_ids": ",".join(rule_ids),
                    "source": "policy_evaluation_node",
                },
            )
            _emit_outcome_audit(
                services=services,
                task_id=task_id,
                trace_id=task.trace_id,
                request_id=task.request_id,
                principal_id=task.principal_id,
                principal_role=task.principal_role,
                outcome="denied",
                error_code=policy_outcome.error_code or "policy_blocked",
                message=policy_outcome.message,
                source="policy_runtime",
                policy_version=policy_version,
                policy_hash=policy_hash,
                rule_ids=rule_ids,
                attributes={
                    "decision": policy_decision,
                    "policy_version": policy_version,
                    "policy_hash": policy_hash,
                    "rule_ids": ",".join(rule_ids),
                },
            )
            return {
                "policy_decision": policy_decision,
                "policy_version": policy_version,
                "policy_hash": policy_hash,
                "rule_ids": rule_ids,
                "final_state": "blocked",
            }
        services.runtime_state_repo.update_task_status(
            task_id,
            "authorized",
            outcome_source="policy_runtime",
            outcome_error_code=None,
            outcome_message="policy authorized command",
            outcome_details={
                "decision": policy_decision,
                "policy_version": policy_version,
                "policy_hash": policy_hash,
                "rule_ids": ",".join(rule_ids),
            },
        )
        return {
            "policy_decision": policy_decision,
            "policy_version": policy_version,
            "policy_hash": policy_hash,
            "rule_ids": rule_ids,
            "final_state": "authorized",
        }

    return policy_evaluation_node


def make_obligation_check_node(services: WorkflowServices) -> Any:
    def obligation_check_node(state: TaskState) -> dict[str, Any]:
        check_and_increment_hop(state["loop_state"])
        task_id = state["task_id"]
        task = services.runtime_state_repo.get_task_by_id(task_id)
        if task is None:
            return {
                "obligation_satisfied": False,
                "blocking_obligation": "task_not_found",
                "final_state": "failed",
            }
        policy_decision = state.get("policy_decision") or "allow"
        policy_version = state.get("policy_version", "policy-version-unknown")
        policy_hash = state.get("policy_hash", "policy-hash-unknown")
        rule_ids = state.get("rule_ids", ())
        if policy_decision != "allow_with_obligations":
            return {"obligation_satisfied": True, "blocking_obligation": None}
        policy_input = _normalize_policy_input(task_id, services)
        policy_outcome = evaluate_with_fail_closed(policy_input, services.policy_runtime_client)
        if policy_outcome.policy_result is None:
            return {
                "obligation_satisfied": False,
                "blocking_obligation": "policy_result_missing",
                "final_state": "blocked",
            }
        obligation_context = ObligationContext(
            trace_id=task.trace_id,
            task_id=task_id,
            request_id=task.request_id,
            principal_id=task.principal_id,
            principal_role=task.principal_role,
            action=task.command,
            target=task.target,
            project_id=task.project_id,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
            audit_writer=services.audit_writer,  # type: ignore[arg-type]
            runtime_state_repo=services.runtime_state_repo,  # type: ignore[arg-type]
            budget_reservation_service=services.budget_reservation_service,
            task_record=task,
        )
        obligation_result = ObligationDispatcher().apply(
            obligations=policy_outcome.policy_result.obligations,
            context=obligation_context,
        )
        if not obligation_result.all_satisfied and obligation_result.blocking_obligation:
            services.runtime_state_repo.update_task_status(
                task_id,
                "blocked",
                outcome_source="obligation_dispatcher",
                outcome_error_code=obligation_result.blocking_obligation,
                outcome_message=f"obligation '{obligation_result.blocking_obligation}' blocked task",
                outcome_details={
                    "blocking_obligation": obligation_result.blocking_obligation,
                    "policy_version": policy_version,
                    "policy_hash": policy_hash,
                    "rule_ids": ",".join(rule_ids),
                },
            )
            return {
                "obligation_satisfied": False,
                "blocking_obligation": obligation_result.blocking_obligation,
                "final_state": "blocked",
            }
        return {"obligation_satisfied": True, "blocking_obligation": None}

    return obligation_check_node


def make_dispatch_node(services: WorkflowServices) -> Any:
    def dispatch_node(state: TaskState) -> dict[str, Any]:
        check_and_increment_hop(state["loop_state"])
        task_id = state["task_id"]
        task = services.runtime_state_repo.get_task_by_id(task_id)
        if task is None:
            return {
                "dispatch_accepted": False,
                "dispatch_target": None,
                "dispatch_id": None,
                "dispatch_error_code": "task_not_found",
                "llm_execution": None,
                "final_state": "failed",
            }
        policy_version = state.get("policy_version", "policy-version-unknown")
        policy_hash = state.get("policy_hash", "policy-hash-unknown")
        rule_ids = state.get("rule_ids", ())
        with services.tracer.start_span(
            trace_id=task.trace_id,
            name=EXECUTION_SANDBOX_SPAN,
            attributes={"stage": "execution_dispatch"},
        ) as dispatch_span:
            dispatch_span.set_attribute("correlation.task_id", task_id)
            dispatch_outcome = services.task_dispatch_service.dispatch_admitted_task(
                task,
                policy_version=policy_version,
                policy_hash=policy_hash,
                rule_ids=rule_ids,
                loop_state=state["loop_state"],
            )
        llm_execution = None
        if dispatch_outcome.llm_metadata is not None:
            meta = dispatch_outcome.llm_metadata
            llm_execution = {
                "decision": meta.decision,
                "model_selected": meta.model_selected,
                "routing_profile": meta.routing_profile,
                "quota_limit_source": meta.quota_limit_source,
                "usage": {
                    "input_tokens": meta.input_tokens,
                    "output_tokens": meta.output_tokens,
                    "total_tokens": meta.total_tokens,
                    "request_units": meta.request_units,
                },
                "cost": {
                    "estimated_cost_usd": meta.estimated_cost_usd,
                    "actual_cost_usd": meta.actual_cost_usd,
                    "cost_source": meta.cost_source,
                },
                "budget_usage": {
                    "currency_delta_usd": meta.currency_delta_usd,
                    "quota_token_units": meta.quota_token_units,
                },
                "generated_text": meta.generated_text,
                "recipient_role": meta.recipient_role,
                "recipient_id": meta.recipient_id,
                "grounding_sources": list(meta.grounding_source_ids),
            }
        if not dispatch_outcome.accepted:
            dispatch_source = dispatch_outcome.source
            _emit_outcome_audit(
                services=services,
                task_id=task_id,
                trace_id=task.trace_id,
                request_id=task.request_id,
                principal_id=task.principal_id,
                principal_role=task.principal_role,
                outcome="denied",
                error_code=dispatch_outcome.error_code or "execution_dispatch_failed",
                message=dispatch_outcome.message,
                source=dispatch_source,
                policy_version=policy_version,
                policy_hash=policy_hash,
                rule_ids=rule_ids,
                attributes={"dispatch_target": dispatch_outcome.target},
            )
            return {
                "dispatch_accepted": False,
                "dispatch_target": dispatch_outcome.target,
                "dispatch_id": dispatch_outcome.dispatch_id,
                "dispatch_error_code": dispatch_outcome.error_code,
                "llm_execution": llm_execution,
                "final_state": "blocked",
            }
        _emit_outcome_audit(
            services=services,
            task_id=task_id,
            trace_id=task.trace_id,
            request_id=task.request_id,
            principal_id=task.principal_id,
            principal_role=task.principal_role,
            outcome="accepted",
            error_code=None,
            message=dispatch_outcome.message,
            source=f"dispatch_{dispatch_outcome.target}",
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
            attributes={
                "dispatch_target": dispatch_outcome.target,
                "dispatch_id": dispatch_outcome.dispatch_id or "dispatch-id-missing",
                "replayed": str(dispatch_outcome.replayed).lower(),
            },
        )
        return {
            "dispatch_accepted": True,
            "dispatch_target": dispatch_outcome.target,
            "dispatch_id": dispatch_outcome.dispatch_id or f"dispatch-{task_id}",
            "dispatch_error_code": None,
            "llm_execution": llm_execution,
            "final_state": "dispatched",
        }

    return dispatch_node
