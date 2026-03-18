"""Policy obligation application — ObligationDispatcher.

Applies obligations from allow_with_obligations policy decisions in
deterministic order: emit_audit_event → require_owner_approval → reserve_budget
→ enforce_sandbox_profile.

An unsatisfied blocking obligation prevents task execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openqilin.budget_runtime.reservation_service import BudgetReservationService
    from openqilin.data_access.repositories.postgres.task_repository import PostgresTaskRepository
    from openqilin.data_access.repositories.runtime_state import TaskRecord
    from openqilin.observability.testing.stubs import InMemoryAuditWriter

# Deterministic obligation execution order (POL-005)
_OBLIGATION_ORDER = (
    "emit_audit_event",
    "require_owner_approval",
    "reserve_budget",
    "enforce_sandbox_profile",
)


@dataclass(frozen=True, slots=True)
class ObligationContext:
    """Runtime context threaded through obligation handlers."""

    trace_id: str
    task_id: str
    request_id: str
    principal_id: str
    principal_role: str
    action: str
    target: str
    project_id: str | None
    policy_version: str
    policy_hash: str
    rule_ids: tuple[str, ...]
    audit_writer: InMemoryAuditWriter
    runtime_state_repo: PostgresTaskRepository
    budget_reservation_service: BudgetReservationService
    task_record: TaskRecord


@dataclass(frozen=True, slots=True)
class ObligationOutcome:
    """Result of applying a single obligation handler."""

    obligation: str
    satisfied: bool
    blocking: bool
    reason: str


@dataclass(frozen=True, slots=True)
class ObligationApplicationResult:
    """Aggregate result of applying all obligations for a policy decision."""

    all_satisfied: bool
    outcomes: tuple[ObligationOutcome, ...]
    blocking_obligation: str | None


class ObligationDispatcher:
    """Apply obligation handlers in deterministic order.

    Stops at first blocking unsatisfied obligation.
    """

    def apply(
        self,
        obligations: tuple[str, ...],
        context: ObligationContext,
    ) -> ObligationApplicationResult:
        """Apply obligations in canonical order. Stops at first blocking failure."""
        outcomes: list[ObligationOutcome] = []

        ordered = [o for o in _OBLIGATION_ORDER if o in obligations]
        for extra in obligations:
            if extra not in _OBLIGATION_ORDER:
                ordered.append(extra)

        blocking_obligation: str | None = None
        for obligation in ordered:
            outcome = _dispatch_obligation(obligation, context)
            outcomes.append(outcome)
            if not outcome.satisfied and outcome.blocking:
                blocking_obligation = obligation
                break

        all_satisfied = all(o.satisfied for o in outcomes)
        return ObligationApplicationResult(
            all_satisfied=all_satisfied,
            outcomes=tuple(outcomes),
            blocking_obligation=blocking_obligation,
        )


def _dispatch_obligation(obligation: str, context: ObligationContext) -> ObligationOutcome:
    handlers = {
        "emit_audit_event": _handle_emit_audit_event,
        "require_owner_approval": _handle_require_owner_approval,
        "reserve_budget": _handle_reserve_budget,
        "enforce_sandbox_profile": _handle_enforce_sandbox_profile,
    }
    handler = handlers.get(obligation)
    if handler is None:
        return ObligationOutcome(
            obligation=obligation,
            satisfied=False,
            blocking=True,
            reason=f"unknown obligation '{obligation}' — fail-closed",
        )
    return handler(context)


def _handle_emit_audit_event(context: ObligationContext) -> ObligationOutcome:
    """Emit immutable obligation audit record (AUD-001). Non-blocking on failure."""
    try:
        context.audit_writer.write_event(
            event_type="obligation.emit_audit_event",
            outcome="applied",
            trace_id=context.trace_id,
            request_id=context.request_id,
            task_id=context.task_id,
            principal_id=context.principal_id,
            principal_role=context.principal_role,
            source="obligation_dispatcher",
            reason_code="obligation_applied",
            message="emit_audit_event obligation satisfied: immutable audit record written",
            policy_version=context.policy_version,
            policy_hash=context.policy_hash,
            rule_ids=context.rule_ids,
            attributes={
                "obligation": "emit_audit_event",
                "action": context.action,
                "target": context.target,
                "project_id": context.project_id or "",
            },
        )
        return ObligationOutcome(
            obligation="emit_audit_event",
            satisfied=True,
            blocking=False,
            reason="immutable audit record emitted",
        )
    except Exception as exc:
        return ObligationOutcome(
            obligation="emit_audit_event",
            satisfied=False,
            blocking=False,
            reason=f"audit write failed (non-blocking in M12): {exc}",
        )


def _handle_require_owner_approval(context: ObligationContext) -> ObligationOutcome:
    """Block task; transition to blocked/approval_required."""
    context.runtime_state_repo.update_task_status(
        context.task_id,
        "blocked",
        outcome_source="obligation_dispatcher",
        outcome_error_code="approval_required",
        outcome_message=(
            "require_owner_approval obligation: task blocked pending explicit owner approval"
        ),
        outcome_details={
            "obligation": "require_owner_approval",
            "principal_id": context.principal_id,
            "action": context.action,
            "target": context.target,
        },
    )
    return ObligationOutcome(
        obligation="require_owner_approval",
        satisfied=False,
        blocking=True,
        reason="task blocked pending owner approval",
    )


def _handle_reserve_budget(context: ObligationContext) -> ObligationOutcome:
    """Reserve budget for costed action (M12 stub; real ledger wired in M14-WP1)."""
    try:
        outcome = context.budget_reservation_service.reserve_with_fail_closed(context.task_record)
    except Exception as exc:
        return ObligationOutcome(
            obligation="reserve_budget",
            satisfied=False,
            blocking=True,
            reason=f"budget reservation failed — fail-closed: {exc}",
        )
    if outcome.allowed:
        reservation_id = outcome.reservation.reservation_id if outcome.reservation else "unknown"
        return ObligationOutcome(
            obligation="reserve_budget",
            satisfied=True,
            blocking=False,
            reason=f"budget reserved: {reservation_id}",
        )
    return ObligationOutcome(
        obligation="reserve_budget",
        satisfied=False,
        blocking=True,
        reason=f"budget failed — fail-closed: {outcome.message}",
    )


def _handle_enforce_sandbox_profile(context: ObligationContext) -> ObligationOutcome:
    """Bind seccomp sandbox profile via SandboxProfileEnforcer (M13-WP6).

    Calls SandboxProfileEnforcer.bind(dispatch_target, profile) to resolve and
    bind the seccomp profile for the target agent.  Fail-closed: unknown profile
    → obligation not satisfied, blocking=False (non-fatal in M13; full enforcement
    in post-MVP-v2).
    """
    from openqilin.execution_sandbox.profiles.enforcement import (
        SandboxProfileEnforcer,
        SandboxProfileNotFoundError,
    )

    enforcer = SandboxProfileEnforcer()
    try:
        enforcer.bind(dispatch_target=context.target, profile_name="default")
    except SandboxProfileNotFoundError as exc:
        return ObligationOutcome(
            obligation="enforce_sandbox_profile",
            satisfied=False,
            blocking=False,
            reason=str(exc),
        )
    return ObligationOutcome(
        obligation="enforce_sandbox_profile",
        satisfied=True,
        blocking=False,
        reason=(
            f"seccomp profile 'default' bound for target '{context.target}' "
            "(M13-WP6 hook; BPF application deferred to post-MVP-v2)"
        ),
    )
