"""Unit tests for M12-WP6: Security Hardening (C-6, C-8).

Tests cover:
- C-6: resolve_principal with identity_repo:
    - unverified identity → PrincipalResolutionError
    - verified identity → role from DB record (not from header)
    - internal connector bypasses DB check
- C-8: GovernedWriteToolService uses context.principal_role (not recipient_role)
    for access check
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from openqilin.control_plane.identity.principal_resolver import (
    Principal,
    PrincipalResolutionError,
    resolve_principal,
)
from openqilin.data_access.repositories.identity_channels import IdentityChannelMappingRecord
from tests.testing.infra_stubs import InMemoryIdentityChannelRepository
from openqilin.execution_sandbox.tools.contracts import ToolCallContext
from openqilin.execution_sandbox.tools.write_tools import GovernedWriteToolService
from openqilin.observability.testing.stubs import InMemoryAuditWriter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    *,
    connector: str = "discord",
    actor_external_id: str = "user-001",
    status: str = "verified",
    principal_role: str = "owner",
) -> IdentityChannelMappingRecord:
    now = datetime.now(tz=UTC)
    return IdentityChannelMappingRecord(
        mapping_id="mapping-001",
        connector=connector,
        actor_external_id=actor_external_id,
        guild_id="guild-001",
        channel_id="channel-001",
        channel_type="text",
        status=status,  # type: ignore[arg-type]
        created_at=now,
        updated_at=now,
        principal_role=principal_role,
    )


def _discord_headers(actor_id: str = "user-001") -> dict[str, str]:
    return {
        "x-external-channel": "discord",
        "x-openqilin-actor-external-id": actor_id,
        "x-openqilin-actor-role": "owner",  # header role should be IGNORED when identity_repo set
    }


# ---------------------------------------------------------------------------
# C-6: resolve_principal with identity_repo
# ---------------------------------------------------------------------------


def test_resolve_principal_unverified_identity_denied() -> None:
    """Persistent repo + no verified mapping → PrincipalResolutionError.

    The verified-identity gate only applies when using a persistent (Postgres)
    identity store; simulated here with a mock that has _session_factory.
    """
    repo = MagicMock()
    repo._session_factory = MagicMock()  # mark as persistent store
    repo.get_by_connector_actor.return_value = None  # actor unknown

    with pytest.raises(PrincipalResolutionError) as exc_info:
        resolve_principal(_discord_headers(), identity_repo=repo)

    assert exc_info.value.code == "principal_identity_unverified"


def test_resolve_principal_pending_identity_denied() -> None:
    """Persistent repo + pending mapping → PrincipalResolutionError.

    The verified-identity gate only applies when using a persistent (Postgres)
    identity store; simulated here with a mock that has _session_factory.
    """
    repo = MagicMock()
    repo._session_factory = MagicMock()  # mark as persistent store
    repo.get_by_connector_actor.return_value = _make_record(status="pending")

    with pytest.raises(PrincipalResolutionError) as exc_info:
        resolve_principal(_discord_headers(), identity_repo=repo)

    assert exc_info.value.code == "principal_identity_unverified"


def test_resolve_principal_verified_identity_uses_db_role() -> None:
    """Verified identity → role comes from DB record, not from x-openqilin-actor-role header."""
    repo = InMemoryIdentityChannelRepository()
    repo.claim_mapping(
        connector="discord",
        actor_external_id="user-001",
        guild_id="guild-001",
        channel_id="channel-001",
        channel_type="text",
        principal_role="ceo",  # DB role is ceo
    )
    repo.set_mapping_status(
        connector="discord",
        actor_external_id="user-001",
        guild_id="guild-001",
        channel_id="channel-001",
        channel_type="text",
        status="verified",
    )

    headers = {
        "x-external-channel": "discord",
        "x-openqilin-actor-external-id": "user-001",
        "x-openqilin-actor-role": "owner",  # header says owner, DB says ceo
    }
    principal = resolve_principal(headers, identity_repo=repo)

    assert isinstance(principal, Principal)
    assert principal.principal_role == "ceo"  # DB role wins, not header
    assert principal.principal_id == "user-001"


def test_resolve_principal_verified_header_role_ignored() -> None:
    """Header role is ignored even when the actor tries to escalate it."""
    repo = InMemoryIdentityChannelRepository()
    repo.claim_mapping(
        connector="discord",
        actor_external_id="attacker",
        guild_id="g",
        channel_id="c",
        channel_type="text",
        principal_role="auditor",  # DB role is auditor
    )
    repo.set_mapping_status(
        connector="discord",
        actor_external_id="attacker",
        guild_id="g",
        channel_id="c",
        channel_type="text",
        status="verified",
    )

    headers = {
        "x-external-channel": "discord",
        "x-openqilin-actor-external-id": "attacker",
        "x-openqilin-actor-role": "owner",  # escalation attempt
    }
    principal = resolve_principal(headers, identity_repo=repo)

    assert principal.principal_role == "auditor"  # escalation blocked


def test_resolve_principal_internal_connector_skips_db_check() -> None:
    """Internal connector bypasses DB verification and uses header role."""
    repo = InMemoryIdentityChannelRepository()
    # No verified records — but internal connector should not need DB

    headers = {
        "x-external-channel": "internal",
        "x-openqilin-actor-external-id": "service-account",
        "x-openqilin-actor-role": "administrator",
    }
    principal = resolve_principal(headers, identity_repo=repo)

    assert principal.principal_role == "administrator"
    assert principal.connector == "internal"
    assert principal.trust_domain == "internal"


def test_resolve_principal_no_identity_repo_uses_header_role() -> None:
    """Without identity_repo (legacy admin path), role comes from header."""
    headers = {
        "x-external-channel": "discord",
        "x-openqilin-actor-external-id": "user-001",
        "x-openqilin-actor-role": "ceo",
    }
    principal = resolve_principal(headers)  # no identity_repo

    assert principal.principal_role == "ceo"


def test_resolve_principal_identity_repo_mock_lookup() -> None:
    """identity_repo.get_by_connector_actor is called with correct arguments."""
    repo = MagicMock()
    repo.get_by_connector_actor.return_value = _make_record(principal_role="project_manager")

    headers = {
        "x-external-channel": "discord",
        "x-openqilin-actor-external-id": "user-pm",
    }
    principal = resolve_principal(headers, identity_repo=repo)

    repo.get_by_connector_actor.assert_called_once_with("discord", "user-pm")
    assert principal.principal_role == "project_manager"


# ---------------------------------------------------------------------------
# C-6: IdentityChannelMappingRecord.principal_role field
# ---------------------------------------------------------------------------


def test_identity_mapping_record_default_principal_role() -> None:
    """Default principal_role on IdentityChannelMappingRecord is 'owner'."""
    now = datetime.now(tz=UTC)
    record = IdentityChannelMappingRecord(
        mapping_id="m",
        connector="discord",
        actor_external_id="u",
        guild_id="g",
        channel_id="c",
        channel_type="text",
        status="pending",
        created_at=now,
        updated_at=now,
    )
    assert record.principal_role == "owner"


def test_identity_mapping_record_custom_principal_role() -> None:
    """IdentityChannelMappingRecord stores custom principal_role."""
    record = _make_record(principal_role="cso")
    assert record.principal_role == "cso"


def test_inmemory_repo_claim_mapping_stores_principal_role() -> None:
    """claim_mapping stores the provided principal_role."""
    repo = InMemoryIdentityChannelRepository()
    record = repo.claim_mapping(
        connector="discord",
        actor_external_id="u",
        guild_id="g",
        channel_id="c",
        channel_type="text",
        principal_role="ceo",
    )
    assert record.principal_role == "ceo"


def test_inmemory_repo_get_by_connector_actor_returns_verified() -> None:
    """get_by_connector_actor returns the verified mapping."""
    repo = InMemoryIdentityChannelRepository()
    repo.claim_mapping(
        connector="discord",
        actor_external_id="u",
        guild_id="g",
        channel_id="c",
        channel_type="text",
        principal_role="cwo",
    )
    repo.set_mapping_status(
        connector="discord",
        actor_external_id="u",
        guild_id="g",
        channel_id="c",
        channel_type="text",
        status="verified",
    )

    record = repo.get_by_connector_actor("discord", "u")
    assert record is not None
    assert record.principal_role == "cwo"
    assert record.status == "verified"


def test_inmemory_repo_get_by_connector_actor_pending_returns_none() -> None:
    """get_by_connector_actor returns None if only pending record exists."""
    repo = InMemoryIdentityChannelRepository()
    repo.claim_mapping(
        connector="discord",
        actor_external_id="u",
        guild_id="g",
        channel_id="c",
        channel_type="text",
    )
    assert repo.get_by_connector_actor("discord", "u") is None


def test_inmemory_repo_get_by_connector_actor_not_found() -> None:
    """get_by_connector_actor returns None for unknown actor."""
    repo = InMemoryIdentityChannelRepository()
    assert repo.get_by_connector_actor("discord", "nobody") is None


# ---------------------------------------------------------------------------
# C-8: GovernedWriteToolService uses principal_role for access check
# ---------------------------------------------------------------------------


def _build_tool_context(
    *,
    principal_role: str,
    recipient_role: str,
) -> ToolCallContext:
    return ToolCallContext(
        task_id="task-001",
        request_id="req-001",
        trace_id="trace-001",
        principal_id="user-001",
        principal_role=principal_role,
        recipient_role=recipient_role,
        recipient_id=None,
        project_id=None,
    )


def _build_write_service() -> GovernedWriteToolService:
    from tests.testing.infra_stubs import InMemoryProjectArtifactRepository
    from tests.testing.infra_stubs import InMemoryGovernanceRepository

    return GovernedWriteToolService(
        governance_repository=InMemoryGovernanceRepository(),
        project_artifact_repository=InMemoryProjectArtifactRepository(),
        audit_writer=InMemoryAuditWriter(),
    )


def test_write_tool_denied_when_principal_role_insufficient() -> None:
    """Requester with insufficient principal_role is denied, regardless of recipient_role."""
    service = _build_write_service()
    # "auditor" is not allowed to call transition_project_lifecycle
    context = _build_tool_context(principal_role="auditor", recipient_role="ceo")

    result = service.call_tool(
        tool_name="transition_project_lifecycle",
        arguments={"next_status": "paused"},
        context=context,
    )

    assert result.decision == "denied"
    assert result.error_code == "tool_access_denied"


def test_write_tool_allowed_when_principal_role_sufficient() -> None:
    """Requester with sufficient principal_role passes the access check (proceeds to next guard)."""
    service = _build_write_service()
    # "ceo" is allowed to call transition_project_lifecycle; will fail at project lookup
    context = _build_tool_context(principal_role="ceo", recipient_role="auditor")

    result = service.call_tool(
        tool_name="transition_project_lifecycle",
        arguments={"project_id": "no-such-project", "next_status": "paused"},
        context=context,
    )

    # Denied at project lookup (not at access check) — error code differs
    assert result.error_code != "tool_access_denied"


def test_write_tool_access_check_ignores_recipient_role() -> None:
    """Access check uses principal_role, not recipient_role; recipient_role cannot grant access."""
    service = _build_write_service()
    # principal is "auditor" (insufficient), recipient is "ceo" (sufficient)
    # Before C-8 fix, recipient_role "ceo" would have passed the access check.
    context = _build_tool_context(principal_role="auditor", recipient_role="ceo")

    result = service.call_tool(
        tool_name="transition_project_lifecycle",
        arguments={"next_status": "paused"},
        context=context,
    )

    assert result.decision == "denied"
    assert result.error_code == "tool_access_denied"
