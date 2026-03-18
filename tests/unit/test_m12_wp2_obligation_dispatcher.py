"""M12-WP2: ObligationDispatcher unit tests.

Tests:
- emit_audit_event fires before other obligations
- require_owner_approval transitions task to blocked; returns satisfied=False blocking=True
- reserve_budget: allowed → satisfied; denied → blocked; fail-closed on exception
- enforce_sandbox_profile: known target → satisfied; unknown target → non-blocking
- Deterministic obligation order maintained
- allow_with_obligations triggers dispatcher; allow passes through without dispatcher
"""

from __future__ import annotations

from unittest.mock import MagicMock

from openqilin.policy_runtime_integration.obligations import (
    ObligationContext,
    ObligationDispatcher,
)


def _make_context(**overrides: object) -> ObligationContext:
    audit_writer = MagicMock()
    audit_writer.write_event.return_value = MagicMock()
    runtime_state_repo = MagicMock()
    budget_service = MagicMock()
    reservation = MagicMock()
    reservation.status = "reserved"
    reservation.reservation_id = "res-001"
    budget_outcome = MagicMock()
    budget_outcome.allowed = True
    budget_outcome.reservation = reservation
    budget_outcome.message = "allowed"
    budget_service.reserve_with_fail_closed.return_value = budget_outcome
    task_record = MagicMock()

    ctx: dict = {
        "trace_id": "trace-001",
        "task_id": "task-001",
        "request_id": "req-001",
        "principal_id": "owner_001",
        "principal_role": "owner",
        "action": "msg_notify",
        "target": "ceo",
        "project_id": None,
        "policy_version": "v2",
        "policy_hash": "abc",
        "rule_ids": ("AUTH-002",),
        "audit_writer": audit_writer,
        "runtime_state_repo": runtime_state_repo,
        "budget_reservation_service": budget_service,
        "task_record": task_record,
    }
    ctx.update(overrides)
    return ObligationContext(**ctx)  # type: ignore[arg-type]


class TestEmitAuditEventObligation:
    def test_emit_audit_event_satisfied(self) -> None:
        ctx = _make_context()
        result = ObligationDispatcher().apply(("emit_audit_event",), ctx)
        assert result.all_satisfied
        ctx.audit_writer.write_event.assert_called_once()  # type: ignore[attr-defined]
        call_kwargs = ctx.audit_writer.write_event.call_args.kwargs  # type: ignore[attr-defined]
        assert call_kwargs["event_type"] == "obligation.emit_audit_event"

    def test_emit_audit_event_fires_first(self) -> None:
        """emit_audit_event must be the first outcome even with multiple obligations."""
        ctx = _make_context()
        result = ObligationDispatcher().apply(("emit_audit_event", "enforce_sandbox_profile"), ctx)
        assert result.outcomes[0].obligation == "emit_audit_event"

    def test_emit_audit_event_non_blocking_on_failure(self) -> None:
        ctx = _make_context()
        ctx.audit_writer.write_event.side_effect = RuntimeError("db down")  # type: ignore[attr-defined]
        result = ObligationDispatcher().apply(("emit_audit_event",), ctx)
        # Non-blocking — all_satisfied=False but no blocking_obligation
        assert not result.all_satisfied
        assert result.blocking_obligation is None


class TestRequireOwnerApprovalObligation:
    def test_require_owner_approval_blocks_task(self) -> None:
        ctx = _make_context()
        result = ObligationDispatcher().apply(("require_owner_approval",), ctx)
        assert not result.all_satisfied
        assert result.blocking_obligation == "require_owner_approval"
        ctx.runtime_state_repo.update_task_status.assert_called_once()  # type: ignore[attr-defined]
        call_args = ctx.runtime_state_repo.update_task_status.call_args  # type: ignore[attr-defined]
        assert call_args.args[1] == "blocked"
        assert call_args.kwargs["outcome_error_code"] == "approval_required"

    def test_require_owner_approval_outcome_blocking(self) -> None:
        ctx = _make_context()
        result = ObligationDispatcher().apply(("require_owner_approval",), ctx)
        outcome = result.outcomes[0]
        assert outcome.obligation == "require_owner_approval"
        assert not outcome.satisfied
        assert outcome.blocking


class TestReserveBudgetObligation:
    def test_reserve_budget_satisfied_when_allowed(self) -> None:
        ctx = _make_context()
        result = ObligationDispatcher().apply(("reserve_budget",), ctx)
        assert result.all_satisfied
        outcome = result.outcomes[0]
        assert outcome.obligation == "reserve_budget"
        assert outcome.satisfied

    def test_reserve_budget_blocks_when_denied(self) -> None:
        ctx = _make_context()
        budget_outcome = MagicMock()
        budget_outcome.allowed = False
        budget_outcome.message = "over budget"
        budget_outcome.reservation = None
        ctx.budget_reservation_service.reserve_with_fail_closed.return_value = budget_outcome  # type: ignore[attr-defined]
        result = ObligationDispatcher().apply(("reserve_budget",), ctx)
        assert not result.all_satisfied
        assert result.blocking_obligation == "reserve_budget"

    def test_reserve_budget_fail_closed_on_exception(self) -> None:
        ctx = _make_context()
        ctx.budget_reservation_service.reserve_with_fail_closed.side_effect = RuntimeError(  # type: ignore[attr-defined]
            "service down"
        )
        result = ObligationDispatcher().apply(("reserve_budget",), ctx)
        assert not result.all_satisfied
        assert result.blocking_obligation == "reserve_budget"


class TestEnforceSandboxProfileObligation:
    def test_known_target_satisfied(self) -> None:
        ctx = _make_context(target="ceo")
        result = ObligationDispatcher().apply(("enforce_sandbox_profile",), ctx)
        outcome = result.outcomes[0]
        assert outcome.satisfied

    def test_any_target_binds_default_profile(self) -> None:
        """M13-WP6: all targets bind to 'default' seccomp profile; outcome is satisfied."""
        ctx = _make_context(target="unknown_agent")
        result = ObligationDispatcher().apply(("enforce_sandbox_profile",), ctx)
        outcome = result.outcomes[0]
        assert outcome.satisfied  # default profile exists; any target can bind to it
        assert not outcome.blocking  # non-blocking in M13 (hook only)
        assert result.blocking_obligation is None


class TestObligationOrder:
    def test_emit_audit_event_before_require_owner_approval(self) -> None:
        ctx = _make_context()
        result = ObligationDispatcher().apply(("require_owner_approval", "emit_audit_event"), ctx)
        # emit_audit_event should run first even if listed second
        assert result.outcomes[0].obligation == "emit_audit_event"

    def test_stops_at_first_blocking_failure(self) -> None:
        """After require_owner_approval blocks, subsequent obligations not evaluated."""
        ctx = _make_context()
        result = ObligationDispatcher().apply(
            ("emit_audit_event", "require_owner_approval", "reserve_budget"), ctx
        )
        # Should stop after require_owner_approval (blocking)
        obligation_names = [o.obligation for o in result.outcomes]
        assert "reserve_budget" not in obligation_names
        assert result.blocking_obligation == "require_owner_approval"


class TestUnknownObligation:
    def test_unknown_obligation_fail_closed(self) -> None:
        ctx = _make_context()
        result = ObligationDispatcher().apply(("some_future_obligation",), ctx)
        assert not result.all_satisfied
        assert result.blocking_obligation == "some_future_obligation"
