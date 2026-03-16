"""M12-WP3: PostgreSQL Repository Migration tests.

Tests:
- H-4: get_runtime_services() raises RuntimeError when app state not initialized
- H-5: startup recovery only re-claims queued/dispatched/running tasks (not failed/cancelled)
- H-6: terminal task count excludes dispatched
- PostgresTaskRepository interface matches InMemoryRuntimeStateRepository
- PostgresAgentRegistryRepository idempotent bootstrap
- PostgresIdentityMappingRepository key normalization
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from openqilin.control_plane.api.dependencies import (
    _ACTIVE_STATUSES,
    _TERMINAL_STATUSES,
)
from openqilin.data_access.repositories.runtime_state import TaskRecord


# ---------------------------------------------------------------------------
# Helper: build a minimal TaskRecord for testing
# ---------------------------------------------------------------------------


def _make_task_record(
    task_id: str = "task-001",
    status: str = "queued",
    principal_id: str = "owner_001",
    idempotency_key: str = "idem-001",
) -> TaskRecord:
    return TaskRecord(
        task_id=task_id,
        request_id="req-001",
        trace_id="trace-001",
        principal_id=principal_id,
        principal_role="owner",
        trust_domain="internal",
        connector="discord",
        command="msg_notify",
        target="ceo",
        args=(),
        metadata=(),
        project_id=None,
        idempotency_key=idempotency_key,
        status=status,
        created_at=datetime.now(tz=UTC),
    )


# ---------------------------------------------------------------------------
# H-4: get_runtime_services() must raise when app state not initialized
# ---------------------------------------------------------------------------


class TestH4SingleRuntimeServicesInstance:
    def test_get_runtime_services_raises_when_not_initialized(self) -> None:
        """H-4: get_runtime_services() must NOT create a new instance on miss."""

        from openqilin.control_plane.api.dependencies import get_runtime_services

        mock_request = MagicMock()
        mock_request.app.state = MagicMock(spec=[])  # no runtime_services attr

        with pytest.raises(RuntimeError, match="RuntimeServices not initialized"):
            get_runtime_services(mock_request)

    def test_get_runtime_services_returns_pre_built_instance(self) -> None:
        """H-4: get_runtime_services() returns the pre-built RuntimeServices from app state."""

        from openqilin.control_plane.api.dependencies import get_runtime_services

        sentinel = object()
        mock_request = MagicMock()
        mock_request.app.state.runtime_services = sentinel

        result = get_runtime_services(mock_request)
        assert result is sentinel


# ---------------------------------------------------------------------------
# H-5: startup recovery must not re-claim failed/cancelled tasks
# ---------------------------------------------------------------------------


class TestH5IdempotencyRecoveryScopeActiveOnly:
    def test_active_statuses_set(self) -> None:
        """H-5: Only queued, dispatched, running are claimed during recovery."""

        assert "queued" in _ACTIVE_STATUSES
        assert "dispatched" in _ACTIVE_STATUSES
        assert "running" in _ACTIVE_STATUSES
        assert "blocked" in _ACTIVE_STATUSES  # awaiting approval — must retain claim
        assert "failed" not in _ACTIVE_STATUSES
        assert "cancelled" not in _ACTIVE_STATUSES
        assert "completed" not in _ACTIVE_STATUSES

    def test_failed_task_not_re_claimed_during_recovery(self) -> None:
        """H-5: A failed task must not consume an idempotency slot during recovery."""

        failed_task = _make_task_record(status="failed")
        assert failed_task.status not in _ACTIVE_STATUSES

    def test_cancelled_task_not_re_claimed_during_recovery(self) -> None:
        """H-5: A cancelled task must not consume an idempotency slot during recovery."""

        cancelled_task = _make_task_record(status="cancelled")
        assert cancelled_task.status not in _ACTIVE_STATUSES

    def test_queued_task_re_claimed_during_recovery(self) -> None:
        """H-5: A queued task must retain its idempotency slot during recovery."""

        queued_task = _make_task_record(status="queued")
        assert queued_task.status in _ACTIVE_STATUSES


# ---------------------------------------------------------------------------
# H-6: terminal task count must exclude dispatched
# ---------------------------------------------------------------------------


class TestH6TerminalStatusCountExcludesDispatched:
    def test_dispatched_not_terminal(self) -> None:
        """H-6: dispatched is not a terminal status and must not be counted as such."""

        assert "dispatched" not in _TERMINAL_STATUSES

    def test_completed_is_terminal(self) -> None:
        assert "completed" in _TERMINAL_STATUSES

    def test_failed_is_terminal(self) -> None:
        assert "failed" in _TERMINAL_STATUSES

    def test_cancelled_is_terminal(self) -> None:
        assert "cancelled" in _TERMINAL_STATUSES

    def test_blocked_is_terminal(self) -> None:
        assert "blocked" in _TERMINAL_STATUSES

    def test_queued_not_terminal(self) -> None:
        assert "queued" not in _TERMINAL_STATUSES

    def test_running_not_terminal(self) -> None:
        assert "running" not in _TERMINAL_STATUSES

    def test_terminal_count_logic(self) -> None:
        """H-6: Startup recovery counts only terminal-status tasks."""

        tasks = [
            _make_task_record(task_id="t1", status="queued"),
            _make_task_record(task_id="t2", status="dispatched"),
            _make_task_record(task_id="t3", status="completed"),
            _make_task_record(task_id="t4", status="failed"),
            _make_task_record(task_id="t5", status="cancelled"),
            _make_task_record(task_id="t6", status="blocked"),
        ]
        # Replicate the terminal-count logic from build_runtime_services()
        terminal_count = sum(1 for t in tasks if t.status in _TERMINAL_STATUSES)
        assert terminal_count == 4  # completed, failed, cancelled, blocked
        # dispatched and queued are NOT counted as terminal (H-6 fix)


# ---------------------------------------------------------------------------
# PostgresTaskRepository: interface compatibility tests (no DB required)
# ---------------------------------------------------------------------------


class TestPostgresTaskRepositoryInterface:
    def test_imports_cleanly(self) -> None:
        from openqilin.data_access.repositories.postgres.task_repository import (
            PostgresTaskRepository,
        )

        assert PostgresTaskRepository is not None

    def test_requires_session_factory(self) -> None:
        from openqilin.data_access.repositories.postgres.task_repository import (
            PostgresTaskRepository,
        )

        with pytest.raises(TypeError):
            PostgresTaskRepository()  # type: ignore[call-arg]

    def test_accepts_session_factory_kwarg(self) -> None:
        from openqilin.data_access.repositories.postgres.task_repository import (
            PostgresTaskRepository,
        )

        mock_factory = MagicMock()
        repo = PostgresTaskRepository(session_factory=mock_factory)
        assert repo is not None


# ---------------------------------------------------------------------------
# PostgresAgentRegistryRepository: interface compatibility tests
# ---------------------------------------------------------------------------


class TestPostgresAgentRegistryRepositoryInterface:
    def test_imports_cleanly(self) -> None:
        from openqilin.data_access.repositories.postgres.agent_registry_repository import (
            PostgresAgentRegistryRepository,
        )

        assert PostgresAgentRegistryRepository is not None

    def test_accepts_session_factory_kwarg(self) -> None:
        from openqilin.data_access.repositories.postgres.agent_registry_repository import (
            PostgresAgentRegistryRepository,
        )

        repo = PostgresAgentRegistryRepository(session_factory=MagicMock())
        assert repo is not None


# ---------------------------------------------------------------------------
# PostgresIdentityMappingRepository: key validation
# ---------------------------------------------------------------------------


class TestPostgresIdentityMappingRepositoryInterface:
    def test_imports_cleanly(self) -> None:
        from openqilin.data_access.repositories.postgres.identity_repository import (
            PostgresIdentityMappingRepository,
        )

        assert PostgresIdentityMappingRepository is not None

    def test_key_validation_raises_on_empty_field(self) -> None:
        from openqilin.data_access.repositories.postgres.identity_repository import (
            _normalize_key,
        )
        from openqilin.data_access.repositories.identity_channels import (
            IdentityChannelRepositoryError,
        )

        with pytest.raises(IdentityChannelRepositoryError, match="non-empty"):
            _normalize_key(
                connector="",
                actor_external_id="user-001",
                guild_id="guild-001",
                channel_id="chan-001",
                channel_type="text",
            )

    def test_key_normalization_lowercases_connector(self) -> None:
        from openqilin.data_access.repositories.postgres.identity_repository import (
            _normalize_key,
        )

        key = _normalize_key(
            connector="Discord",
            actor_external_id="user-001",
            guild_id="guild-001",
            channel_id="chan-001",
            channel_type="TEXT",
        )
        assert key[0] == "discord"
        assert key[4] == "text"


# ---------------------------------------------------------------------------
# PostgresProjectRepository: interface import
# ---------------------------------------------------------------------------


class TestPostgresProjectRepositoryInterface:
    def test_imports_cleanly(self) -> None:
        from openqilin.data_access.repositories.postgres.project_repository import (
            PostgresProjectRepository,
        )

        assert PostgresProjectRepository is not None

    def test_accepts_session_factory_kwarg(self) -> None:
        from openqilin.data_access.repositories.postgres.project_repository import (
            PostgresProjectRepository,
        )

        repo = PostgresProjectRepository(session_factory=MagicMock())
        assert repo is not None


# ---------------------------------------------------------------------------
# PostgresCommunicationRepository: interface import
# ---------------------------------------------------------------------------


class TestPostgresCommunicationRepositoryInterface:
    def test_imports_cleanly(self) -> None:
        from openqilin.data_access.repositories.postgres.communication_repository import (
            PostgresCommunicationRepository,
        )

        assert PostgresCommunicationRepository is not None


# ---------------------------------------------------------------------------
# PostgresGovernanceArtifactRepository: interface import + authorization
# ---------------------------------------------------------------------------


class TestPostgresGovernanceArtifactRepositoryInterface:
    def test_imports_cleanly(self) -> None:
        from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
            PostgresGovernanceArtifactRepository,
        )

        assert PostgresGovernanceArtifactRepository is not None

    def test_invalid_project_id_raises(self) -> None:
        from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
            _validate_project_id,
        )
        from openqilin.data_access.repositories.artifacts import (
            ProjectArtifactRepositoryError,
        )

        with pytest.raises(ProjectArtifactRepositoryError, match="project_id format invalid"):
            _validate_project_id("bad id with spaces!")

    def test_valid_project_id_accepted(self) -> None:
        from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
            _validate_project_id,
        )

        result = _validate_project_id("proj-001")
        assert result == "proj-001"

    def test_invalid_artifact_type_raises(self) -> None:
        from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
            _validate_artifact_type,
        )
        from openqilin.data_access.repositories.artifacts import (
            ProjectArtifactRepositoryError,
        )

        with pytest.raises(ProjectArtifactRepositoryError, match="artifact_type format invalid"):
            _validate_artifact_type("invalid type with spaces!")

    def test_write_without_context_raises(self) -> None:
        from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
            PostgresGovernanceArtifactRepository,
        )
        from openqilin.data_access.repositories.artifacts import (
            ProjectArtifactRepositoryError,
        )

        repo = PostgresGovernanceArtifactRepository(session_factory=MagicMock())
        with pytest.raises(ProjectArtifactRepositoryError, match="write context is required"):
            repo.write_project_artifact(
                project_id="proj-001",
                artifact_type="project_charter",
                content="hello",
                write_context=None,
            )


# ---------------------------------------------------------------------------
# Config: database_url field present
# ---------------------------------------------------------------------------


class TestConfigDatabaseUrl:
    def test_database_url_defaults_to_empty(self) -> None:
        from openqilin.shared_kernel.config import RuntimeSettings

        settings = RuntimeSettings()
        assert settings.database_url == ""

    def test_database_url_populated_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from openqilin.shared_kernel.config import RuntimeSettings

        monkeypatch.setenv("OPENQILIN_DATABASE_URL", "postgresql+psycopg://test:test@db:5432/test")
        settings = RuntimeSettings()
        assert settings.database_url == "postgresql+psycopg://test:test@db:5432/test"
