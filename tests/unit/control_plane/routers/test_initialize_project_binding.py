from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from openqilin.control_plane.routers.governance import initialize_project
from openqilin.control_plane.schemas.governance import ProjectInitializationRequest


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
