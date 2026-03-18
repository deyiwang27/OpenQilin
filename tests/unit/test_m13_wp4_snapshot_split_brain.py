"""M13-WP4 — H-3 Snapshot Split-Brain Fix.

Verifies:
- InMemoryRuntimeStateRepository has no filesystem snapshot side-effects.
- update_task_status() exception leaves in-memory dict unchanged.
- PostgresTaskRepository.update_task_status() propagates DB write failures.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.task_orchestrator.state.transition_guard import InvalidStateTransitionError
from tests.testing.infra_stubs import InMemoryRuntimeStateRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_queued_task(task_id: str = "t-1") -> TaskRecord:
    return TaskRecord(
        task_id=task_id,
        request_id="req-1",
        trace_id="trace-1",
        principal_id="u-1",
        principal_role="owner",
        trust_domain="openqilin",
        connector="discord",
        command="EXECUTE",
        target="secretary",
        args=(),
        metadata=(),
        project_id=None,
        idempotency_key="idem-1",
        status="queued",
        created_at=datetime.now(tz=UTC),
    )


# ---------------------------------------------------------------------------
# InMemoryRuntimeStateRepository — no filesystem side-effects
# ---------------------------------------------------------------------------


class TestInMemoryRuntimeStateRepositoryNoSnapshot:
    def test_constructor_accepts_no_snapshot_path(self) -> None:
        repo = InMemoryRuntimeStateRepository()
        assert not hasattr(repo, "_snapshot_path")

    def test_create_task_does_not_write_filesystem(self) -> None:
        """No filesystem writes occur after create_task_from_envelope."""
        repo = InMemoryRuntimeStateRepository()
        with patch(
            "pathlib.Path.write_text", side_effect=AssertionError("filesystem write forbidden")
        ):
            pass  # no write_text call expected
        assert repo._task_by_id == {}  # no side-effects

    def test_update_task_status_does_not_write_filesystem(self) -> None:
        repo = InMemoryRuntimeStateRepository()
        task = _make_queued_task()
        repo._task_by_id[task.task_id] = task

        with patch(
            "pathlib.Path.write_text", side_effect=AssertionError("filesystem write forbidden")
        ):
            result = repo.update_task_status(task.task_id, "authorized")

        assert result is not None
        assert result.status == "authorized"

    def test_update_task_status_atomic_on_illegal_transition(self) -> None:
        """If transition guard raises, in-memory dict must NOT be updated."""
        repo = InMemoryRuntimeStateRepository()
        task = _make_queued_task()
        repo._task_by_id[task.task_id] = task

        original_status = task.status
        with pytest.raises(InvalidStateTransitionError):
            repo.update_task_status(task.task_id, "completed")  # queued → completed is illegal

        assert repo._task_by_id[task.task_id].status == original_status

    def test_update_task_returns_none_for_unknown_task(self) -> None:
        repo = InMemoryRuntimeStateRepository()
        result = repo.update_task_status("nonexistent", "dispatched")
        assert result is None


# ---------------------------------------------------------------------------
# PostgresTaskRepository — DB write failure propagation
# ---------------------------------------------------------------------------


class TestPostgresTaskRepositoryDbFailurePropagation:
    def test_update_task_status_propagates_db_exception(self) -> None:
        """If the DB session raises during UPDATE, the exception propagates."""
        from sqlalchemy.exc import OperationalError

        from openqilin.data_access.repositories.postgres.task_repository import (
            PostgresTaskRepository,
        )

        task = _make_queued_task()

        # Session that returns the task on SELECT but fails on UPDATE commit.
        select_row = MagicMock()
        select_row.mappings.return_value.first.return_value = {
            "task_id": task.task_id,
            "request_id": task.request_id,
            "trace_id": task.trace_id,
            "principal_id": task.principal_id,
            "principal_role": task.principal_role,
            "trust_domain": task.trust_domain,
            "connector": task.connector,
            "command": task.command,
            "target": task.target,
            "args": list(task.args),
            "metadata": [list(m) for m in task.metadata],
            "project_id": task.project_id,
            "idempotency_key": task.idempotency_key,
            "status": task.status,
            "created_at": task.created_at,
            "outcome_source": None,
            "outcome_error_code": None,
            "outcome_message": None,
            "outcome_details": None,
            "dispatch_target": None,
            "dispatch_id": None,
        }

        call_count = 0

        def execute_side_effect(stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: SELECT for get_task_by_id
                return select_row
            # Second call: UPDATE — raise to simulate DB write failure
            raise OperationalError("DB down", None, None)

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.execute.side_effect = execute_side_effect

        mock_factory = MagicMock(return_value=mock_session)

        repo = PostgresTaskRepository(session_factory=mock_factory)

        with pytest.raises(OperationalError):
            repo.update_task_status(task.task_id, "authorized")

    def test_update_task_status_illegal_transition_raises_before_db_write(self) -> None:
        """assert_legal_transition() fires before any DB write (durable-write-first)."""
        from openqilin.data_access.repositories.postgres.task_repository import (
            PostgresTaskRepository,
        )

        task = _make_queued_task()

        select_row = MagicMock()
        select_row.mappings.return_value.first.return_value = {
            "task_id": task.task_id,
            "request_id": task.request_id,
            "trace_id": task.trace_id,
            "principal_id": task.principal_id,
            "principal_role": task.principal_role,
            "trust_domain": task.trust_domain,
            "connector": task.connector,
            "command": task.command,
            "target": task.target,
            "args": [],
            "metadata": [],
            "project_id": None,
            "idempotency_key": task.idempotency_key,
            "status": "queued",
            "created_at": task.created_at,
            "outcome_source": None,
            "outcome_error_code": None,
            "outcome_message": None,
            "outcome_details": None,
            "dispatch_target": None,
            "dispatch_id": None,
        }

        update_called = False

        def execute_side_effect(stmt, params=None):
            nonlocal update_called
            # Track if an UPDATE was called (second execute call)
            result = MagicMock()
            result.mappings.return_value.first.return_value = (
                select_row.mappings.return_value.first.return_value
            )
            if update_called:
                raise AssertionError(
                    "UPDATE was called after illegal transition — durable-write-first violated"
                )
            update_called = True
            return result

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.execute.side_effect = execute_side_effect

        mock_factory = MagicMock(return_value=mock_session)
        repo = PostgresTaskRepository(session_factory=mock_factory)

        # queued → completed is illegal; transition guard should fire before UPDATE
        with pytest.raises(InvalidStateTransitionError):
            repo.update_task_status(task.task_id, "completed")
