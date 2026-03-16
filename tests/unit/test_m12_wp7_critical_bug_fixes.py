"""Unit tests for M12-WP7: Critical Runtime Bug Fixes (H-1, H-2).

Tests cover:
- H-1: Fail-open dispatch fallback — unknown targets raise DispatchTargetError and
  transition the task to 'failed' instead of faking a successful dispatch.
- H-2: State transition guard — assert_legal_transition rejects illegal transitions;
  InMemoryRuntimeStateRepository and PostgresTaskRepository both enforce it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from openqilin.data_access.repositories.runtime_state import (
    InMemoryRuntimeStateRepository,
    TaskRecord,
)
from openqilin.task_orchestrator.dispatch.target_selector import DispatchTargetError
from openqilin.task_orchestrator.services.lifecycle_service import TaskLifecycleService
from openqilin.task_orchestrator.services.task_service import TaskDispatchService
from openqilin.task_orchestrator.state.transition_guard import (
    LEGAL_TRANSITIONS,
    InvalidStateTransitionError,
    assert_legal_transition,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(*, status: str = "authorized") -> TaskRecord:
    return TaskRecord(
        task_id="task-001",
        request_id="req-001",
        trace_id="trace-001",
        principal_id="principal-001",
        principal_role="owner",
        trust_domain="test",
        connector="internal",
        command="llm_chat",
        target="secretary",
        args=(),
        metadata=(),
        project_id=None,
        idempotency_key="idem-001",
        status=status,
        created_at=datetime.now(tz=UTC),
    )


def _make_runtime_repo() -> InMemoryRuntimeStateRepository:
    repo = InMemoryRuntimeStateRepository()
    task = _make_task(status="queued")
    repo._task_by_id[task.task_id] = task
    repo._task_id_by_principal_key[(task.principal_id, task.idempotency_key)] = task.task_id
    return repo


# ---------------------------------------------------------------------------
# H-2: assert_legal_transition unit tests
# ---------------------------------------------------------------------------


class TestAssertLegalTransition:
    def test_legal_queued_to_authorized(self) -> None:
        assert_legal_transition("queued", "authorized")

    def test_legal_queued_to_blocked(self) -> None:
        assert_legal_transition("queued", "blocked")

    def test_legal_queued_to_failed(self) -> None:
        assert_legal_transition("queued", "failed")

    def test_legal_authorized_to_dispatched(self) -> None:
        assert_legal_transition("authorized", "dispatched")

    def test_legal_authorized_to_blocked(self) -> None:
        assert_legal_transition("authorized", "blocked")

    def test_legal_authorized_to_failed(self) -> None:
        assert_legal_transition("authorized", "failed")

    def test_legal_dispatched_to_running(self) -> None:
        assert_legal_transition("dispatched", "running")

    def test_legal_dispatched_to_completed(self) -> None:
        assert_legal_transition("dispatched", "completed")

    def test_legal_running_to_completed(self) -> None:
        assert_legal_transition("running", "completed")

    def test_legal_running_to_failed(self) -> None:
        assert_legal_transition("running", "failed")

    def test_legal_blocked_to_queued(self) -> None:
        assert_legal_transition("blocked", "queued")

    def test_illegal_queued_to_dispatched_raises(self) -> None:
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            assert_legal_transition("queued", "dispatched")
        assert exc_info.value.current == "queued"
        assert exc_info.value.next_state == "dispatched"

    def test_illegal_authorized_to_running_raises(self) -> None:
        with pytest.raises(InvalidStateTransitionError):
            assert_legal_transition("authorized", "running")

    def test_illegal_completed_to_anything_raises(self) -> None:
        with pytest.raises(InvalidStateTransitionError):
            assert_legal_transition("completed", "failed")

    def test_illegal_failed_to_anything_raises(self) -> None:
        with pytest.raises(InvalidStateTransitionError):
            assert_legal_transition("failed", "queued")

    def test_illegal_cancelled_to_anything_raises(self) -> None:
        with pytest.raises(InvalidStateTransitionError):
            assert_legal_transition("cancelled", "running")

    def test_unknown_current_state_raises(self) -> None:
        with pytest.raises(InvalidStateTransitionError):
            assert_legal_transition("policy_evaluation", "dispatched")

    def test_error_message_contains_states(self) -> None:
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            assert_legal_transition("completed", "running")
        assert "completed" in str(exc_info.value)
        assert "running" in str(exc_info.value)

    def test_all_terminal_states_have_no_successors(self) -> None:
        for terminal in ("completed", "failed", "cancelled"):
            assert LEGAL_TRANSITIONS[terminal] == frozenset()

    def test_authorized_not_a_terminal_state(self) -> None:
        assert len(LEGAL_TRANSITIONS["authorized"]) > 0


# ---------------------------------------------------------------------------
# H-2: InMemoryRuntimeStateRepository enforces transition guard
# ---------------------------------------------------------------------------


class TestInMemoryRepoTransitionGuard:
    def test_legal_transition_succeeds(self) -> None:
        repo = _make_runtime_repo()
        result = repo.update_task_status("task-001", "authorized")
        assert result is not None
        assert result.status == "authorized"

    def test_illegal_transition_raises(self) -> None:
        repo = _make_runtime_repo()
        with pytest.raises(InvalidStateTransitionError):
            repo.update_task_status("task-001", "running")  # queued → running is illegal

    def test_same_status_is_allowed_for_metadata_update(self) -> None:
        repo = _make_runtime_repo()
        result = repo.update_task_status(
            "task-001",
            "queued",
            outcome_message="metadata refresh",
        )
        assert result is not None
        assert result.status == "queued"

    def test_unknown_task_returns_none(self) -> None:
        repo = _make_runtime_repo()
        result = repo.update_task_status("no-such-task", "authorized")
        assert result is None

    def test_terminal_state_blocks_further_updates(self) -> None:
        repo = _make_runtime_repo()
        # queued → failed (legal)
        repo.update_task_status("task-001", "failed")
        # failed → anything (illegal)
        with pytest.raises(InvalidStateTransitionError):
            repo.update_task_status("task-001", "queued")

    def test_full_happy_path_transitions(self) -> None:
        repo = _make_runtime_repo()
        repo.update_task_status("task-001", "authorized")
        repo.update_task_status("task-001", "dispatched")
        result = repo.update_task_status("task-001", "running")
        assert result is not None
        assert result.status == "running"
        repo.update_task_status("task-001", "completed")
        final = repo.get_task_by_id("task-001")
        assert final is not None
        assert final.status == "completed"


# ---------------------------------------------------------------------------
# H-2: PostgresTaskRepository enforces transition guard (unit — mocked session)
# ---------------------------------------------------------------------------


class TestPostgresRepoTransitionGuard:
    def _build_postgres_repo(self, existing_task: TaskRecord):
        """Build a PostgresTaskRepository whose get_task_by_id returns existing_task."""
        from openqilin.data_access.repositories.postgres.task_repository import (
            PostgresTaskRepository,
        )

        repo = PostgresTaskRepository.__new__(PostgresTaskRepository)
        repo.get_task_by_id = MagicMock(return_value=existing_task)
        # _session_factory not called for illegal transitions
        repo._session_factory = MagicMock()
        return repo

    def test_illegal_transition_raises_before_db_write(self) -> None:
        task = _make_task(status="completed")
        repo = self._build_postgres_repo(task)
        with pytest.raises(InvalidStateTransitionError):
            repo.update_task_status(task.task_id, "running")
        # DB session must NOT have been called
        repo._session_factory.assert_not_called()

    def test_legal_transition_proceeds_to_db(self) -> None:
        task = _make_task(status="authorized")
        repo = self._build_postgres_repo(task)
        # After DB write, get_task_by_id is called again to return the updated record
        updated = _make_task(status="dispatched")
        repo.get_task_by_id = MagicMock(side_effect=[task, updated])

        session_cm = MagicMock()
        session_cm.__enter__ = MagicMock(return_value=MagicMock())
        session_cm.__exit__ = MagicMock(return_value=False)
        repo._session_factory = MagicMock(return_value=session_cm)

        result = repo.update_task_status(task.task_id, "dispatched")
        assert result is not None
        assert result.status == "dispatched"
        repo._session_factory.assert_called_once()


# ---------------------------------------------------------------------------
# H-1: Unknown dispatch target → DispatchTargetError + task marked failed
# ---------------------------------------------------------------------------


class TestDispatchTargetError:
    def _make_dispatch_service(self) -> tuple[TaskDispatchService, InMemoryRuntimeStateRepository]:
        repo = InMemoryRuntimeStateRepository()
        # Insert a task in 'authorized' state (ready for dispatch)
        task = _make_task(status="authorized")
        repo._task_by_id[task.task_id] = task
        repo._task_id_by_principal_key[(task.principal_id, task.idempotency_key)] = task.task_id

        lifecycle = TaskLifecycleService(runtime_state_repo=repo)
        sandbox_adapter = MagicMock()
        llm_adapter = MagicMock()

        service = TaskDispatchService(
            lifecycle_service=lifecycle,
            sandbox_execution_adapter=sandbox_adapter,
            llm_dispatch_adapter=llm_adapter,
        )
        return service, repo

    def test_unknown_target_raises_dispatch_target_error(self) -> None:
        service, repo = self._make_dispatch_service()
        task = next(iter(repo._task_by_id.values()))

        with patch(
            "openqilin.task_orchestrator.services.task_service.select_dispatch_target",
            return_value="totally_unknown",
        ):
            with pytest.raises(DispatchTargetError) as exc_info:
                service.dispatch_admitted_task(task)

        assert "totally_unknown" in exc_info.value.message

    def test_unknown_target_marks_task_as_failed(self) -> None:
        service, repo = self._make_dispatch_service()
        task = next(iter(repo._task_by_id.values()))

        with patch(
            "openqilin.task_orchestrator.services.task_service.select_dispatch_target",
            return_value="totally_unknown",
        ):
            with pytest.raises(DispatchTargetError):
                service.dispatch_admitted_task(task)

        updated = repo.get_task_by_id(task.task_id)
        assert updated is not None
        assert updated.status == "failed"
        assert updated.outcome_error_code == "dispatch_target_unknown"

    def test_unknown_target_outcome_source_is_service(self) -> None:
        service, repo = self._make_dispatch_service()
        task = next(iter(repo._task_by_id.values()))

        with patch(
            "openqilin.task_orchestrator.services.task_service.select_dispatch_target",
            return_value="totally_unknown",
        ):
            with pytest.raises(DispatchTargetError):
                service.dispatch_admitted_task(task)

        updated = repo.get_task_by_id(task.task_id)
        assert updated is not None
        assert updated.outcome_source == "task_dispatch_service"

    def test_known_targets_do_not_raise(self) -> None:
        """Sanity: all three known targets complete without DispatchTargetError."""
        for command_prefix in ("tool_exec", "msg_notify", "sandbox_run"):
            repo = InMemoryRuntimeStateRepository()
            task_for_target = TaskRecord(
                task_id=f"task-{command_prefix}",
                request_id="req-x",
                trace_id="trace-x",
                principal_id="principal-x",
                principal_role="owner",
                trust_domain="test",
                connector="internal",
                command=command_prefix,
                target="secretary",
                args=(),
                metadata=(),
                project_id=None,
                idempotency_key=f"idem-{command_prefix}",
                status="authorized",
                created_at=datetime.now(tz=UTC),
            )
            repo._task_by_id[task_for_target.task_id] = task_for_target
            repo._task_id_by_principal_key[
                (task_for_target.principal_id, task_for_target.idempotency_key)
            ] = task_for_target.task_id

            lifecycle = TaskLifecycleService(runtime_state_repo=repo)

            sandbox_adapter = MagicMock()
            sandbox_adapter.dispatch.return_value = MagicMock(
                accepted=True, dispatch_id="disp-001", message="ok"
            )
            llm_adapter = MagicMock()
            llm_adapter.dispatch.return_value = MagicMock(
                accepted=True,
                dispatch_id="disp-001",
                message="ok",
                recipient_role="owner",
                recipient_id=None,
                grounding_source_ids=(),
                gateway_response=None,
                error_code=None,
            )

            service = TaskDispatchService(
                lifecycle_service=lifecycle,
                sandbox_execution_adapter=sandbox_adapter,
                llm_dispatch_adapter=llm_adapter,
            )

            # Should not raise DispatchTargetError
            try:
                service.dispatch_admitted_task(task_for_target)
            except DispatchTargetError:
                pytest.fail(
                    f"DispatchTargetError raised unexpectedly for command={command_prefix!r}"
                )
