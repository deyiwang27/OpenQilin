from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from openqilin.control_plane.routers.governance import (
    finalize_completion,
    initialize_project,
    terminate_project,
)
from openqilin.control_plane.schemas.governance import (
    ProjectCompletionFinalizeRequest,
    ProjectInitializationRequest,
    ProjectLifecycleActionRequest,
)
from openqilin.project_spaces.models import LifecycleEvent


def _payload(*, guild_id: str | None) -> ProjectInitializationRequest:
    return ProjectInitializationRequest(
        trace_id="trace-m17-wp7",
        objective="Initialize with auto channel",
        budget_currency_total=100.0,
        budget_quota_total=1000.0,
        metric_plan={"delivery": "green"},
        workforce_plan={"project_manager": "1"},
        guild_id=guild_id,
    )


def _outcome() -> SimpleNamespace:
    project = SimpleNamespace(
        name="Website Redesign",
        status="active",
        objective="Initialize with auto channel",
        initialization=None,
    )
    return SimpleNamespace(project=project)


def _completed_outcome() -> SimpleNamespace:
    return SimpleNamespace(project=SimpleNamespace(name="Website Redesign", status="completed"))


def _terminated_outcome() -> SimpleNamespace:
    return SimpleNamespace(
        project=SimpleNamespace(name="Website Redesign", status="terminated"),
        previous_status="active",
    )


def test_initialize_project_calls_binding_service_when_guild_id_provided() -> None:
    """binding_service.create_and_bind() called when guild_id is in payload."""

    binding_service = MagicMock()
    audit_writer = MagicMock()

    with (
        patch(
            "openqilin.control_plane.routers.governance._validate_connector_headers",
            return_value=None,
        ),
        patch(
            "openqilin.control_plane.routers.governance._resolve_principal",
            return_value=("cwo_1", "cwo"),
        ),
        patch(
            "openqilin.control_plane.routers.governance.initialize_project_by_cwo",
            return_value=_outcome(),
        ),
    ):
        response = initialize_project(
            project_id="proj-001",
            payload=_payload(guild_id="guild-001"),
            governance_repository=MagicMock(),
            binding_service=binding_service,
            audit_writer=audit_writer,
        )

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["status"] == "active"
    binding_service.create_and_bind.assert_called_once_with(
        project_id="proj-001",
        guild_id="guild-001",
        project_name="Website Redesign",
    )


def test_initialize_project_skips_binding_when_no_guild_id() -> None:
    """binding_service.create_and_bind() NOT called when guild_id is None."""

    binding_service = MagicMock()

    with (
        patch(
            "openqilin.control_plane.routers.governance._validate_connector_headers",
            return_value=None,
        ),
        patch(
            "openqilin.control_plane.routers.governance._resolve_principal",
            return_value=("cwo_1", "cwo"),
        ),
        patch(
            "openqilin.control_plane.routers.governance.initialize_project_by_cwo",
            return_value=_outcome(),
        ),
    ):
        response = initialize_project(
            project_id="proj-002",
            payload=_payload(guild_id=None),
            governance_repository=MagicMock(),
            binding_service=binding_service,
            audit_writer=MagicMock(),
        )

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body["status"] == "ok"
    binding_service.create_and_bind.assert_not_called()


def test_initialize_project_succeeds_when_channel_creation_fails() -> None:
    """Project initializes successfully even if binding_service.create_and_bind() raises."""

    binding_service = MagicMock()
    binding_service.create_and_bind.side_effect = RuntimeError("discord unavailable")

    with (
        patch(
            "openqilin.control_plane.routers.governance._validate_connector_headers",
            return_value=None,
        ),
        patch(
            "openqilin.control_plane.routers.governance._resolve_principal",
            return_value=("cwo_1", "cwo"),
        ),
        patch(
            "openqilin.control_plane.routers.governance.initialize_project_by_cwo",
            return_value=_outcome(),
        ),
    ):
        response = initialize_project(
            project_id="proj-003",
            payload=_payload(guild_id="guild-003"),
            governance_repository=MagicMock(),
            binding_service=binding_service,
            audit_writer=MagicMock(),
        )

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["status"] == "active"
    binding_service.create_and_bind.assert_called_once()


def test_finalize_completion_archives_channel() -> None:
    """finalize_completion calls binding_service.transition with event_type='archive'."""

    binding_service = MagicMock()
    audit_writer = MagicMock()

    with (
        patch(
            "openqilin.control_plane.routers.governance._validate_connector_headers",
            return_value=None,
        ),
        patch(
            "openqilin.control_plane.routers.governance._resolve_principal",
            return_value=("cwo_1", "cwo"),
        ),
        patch(
            "openqilin.control_plane.routers.governance.finalize_project_completion_by_c_suite",
            return_value=_completed_outcome(),
        ),
    ):
        response = finalize_completion(
            project_id="proj-004",
            payload=ProjectCompletionFinalizeRequest(trace_id="trace-004"),
            governance_repository=MagicMock(),
            binding_service=binding_service,
            audit_writer=audit_writer,
        )

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["status"] == "completed"
    binding_service.transition.assert_called_once_with(
        project_id="proj-004",
        event=LifecycleEvent(event_type="archive"),
        project_name="Website Redesign",
    )


def test_finalize_completion_succeeds_when_archive_fails() -> None:
    """Project completes even if channel archive raises."""

    binding_service = MagicMock()
    binding_service.transition.side_effect = RuntimeError("archive failed")

    with (
        patch(
            "openqilin.control_plane.routers.governance._validate_connector_headers",
            return_value=None,
        ),
        patch(
            "openqilin.control_plane.routers.governance._resolve_principal",
            return_value=("cwo_1", "cwo"),
        ),
        patch(
            "openqilin.control_plane.routers.governance.finalize_project_completion_by_c_suite",
            return_value=_completed_outcome(),
        ),
    ):
        response = finalize_completion(
            project_id="proj-005",
            payload=ProjectCompletionFinalizeRequest(trace_id="trace-005"),
            governance_repository=MagicMock(),
            binding_service=binding_service,
            audit_writer=MagicMock(),
        )

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["status"] == "completed"
    binding_service.transition.assert_called_once()


def test_terminate_project_locks_channel() -> None:
    """terminate_project calls binding_service.transition with event_type='lock'."""

    binding_service = MagicMock()
    audit_writer = MagicMock()

    with (
        patch(
            "openqilin.control_plane.routers.governance._validate_connector_headers",
            return_value=None,
        ),
        patch(
            "openqilin.control_plane.routers.governance._resolve_principal",
            return_value=("ceo_1", "ceo"),
        ),
        patch(
            "openqilin.control_plane.routers.governance.terminate_project_by_governance",
            return_value=_terminated_outcome(),
        ),
    ):
        response = terminate_project(
            project_id="proj-006",
            payload=ProjectLifecycleActionRequest(trace_id="trace-006"),
            governance_repository=MagicMock(),
            binding_service=binding_service,
            audit_writer=audit_writer,
        )

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["status"] == "terminated"
    binding_service.transition.assert_called_once_with(
        project_id="proj-006",
        event=LifecycleEvent(event_type="lock"),
        project_name="Website Redesign",
    )


def test_terminate_project_succeeds_when_lock_fails() -> None:
    """Project terminates even if channel lock raises."""

    binding_service = MagicMock()
    binding_service.transition.side_effect = RuntimeError("lock failed")

    with (
        patch(
            "openqilin.control_plane.routers.governance._validate_connector_headers",
            return_value=None,
        ),
        patch(
            "openqilin.control_plane.routers.governance._resolve_principal",
            return_value=("ceo_1", "ceo"),
        ),
        patch(
            "openqilin.control_plane.routers.governance.terminate_project_by_governance",
            return_value=_terminated_outcome(),
        ),
    ):
        response = terminate_project(
            project_id="proj-007",
            payload=ProjectLifecycleActionRequest(trace_id="trace-007"),
            governance_repository=MagicMock(),
            binding_service=binding_service,
            audit_writer=MagicMock(),
        )

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["data"]["status"] == "terminated"
    binding_service.transition.assert_called_once()
