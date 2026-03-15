"""Unit tests for C-7 fix: unknown chat_class must raise DiscordGovernanceError, not KeyError.

chat_class is a Pydantic Literal in the API schema — unknown values are rejected at
ingress validation. These tests use model_construct() to bypass Pydantic's Literal check
and test the defensive guard in validate_discord_governance directly, covering cases where
the function is called from internal paths or after future schema relaxation.
"""

from __future__ import annotations

import pytest

from openqilin.control_plane.identity.discord_governance import (
    DiscordGovernanceError,
    validate_discord_governance,
)
from openqilin.control_plane.schemas.owner_commands import (
    OwnerCommandConnectorMetadata,
    OwnerCommandDiscordContext,
    OwnerCommandRecipient,
)
from openqilin.control_plane.schemas.owner_commands import OwnerCommandRequest
from openqilin.data_access.repositories.governance import InMemoryGovernanceRepository
from openqilin.data_access.repositories.identity_channels import InMemoryIdentityChannelRepository
from openqilin.testing.owner_command import build_owner_command_request_model


def _build_payload_with_chat_class(chat_class: str) -> OwnerCommandRequest:
    """Build an OwnerCommandRequest with an arbitrary chat_class, bypassing Pydantic Literal."""
    context = OwnerCommandDiscordContext.model_construct(
        guild_id="guild-test",
        channel_id="channel-test",
        channel_type="text",
        chat_class=chat_class,
    )
    connector = OwnerCommandConnectorMetadata.model_construct(
        channel="discord",
        external_message_id="ext-test-001",
        actor_external_id="owner_m11_wp2",
        idempotency_key="idem-m11-wp2-x",
        raw_payload_hash="a" * 64,
        discord_context=context,
    )
    return OwnerCommandRequest.model_construct(
        message_id="msg-test-001",
        trace_id="trace-m11-wp2",
        sender=None,
        recipients=[
            OwnerCommandRecipient.model_construct(recipient_id="sandbox", recipient_type="runtime")
        ],
        message_type="command",
        priority="normal",
        timestamp=None,
        content="test",
        project_id="project_1",
        connector=connector,
        command=None,
    )


def test_unknown_chat_class_raises_governance_error_not_key_error() -> None:
    """C-7: unknown chat_class must raise DiscordGovernanceError, not KeyError."""
    payload = _build_payload_with_chat_class("unknown_class")

    with pytest.raises(DiscordGovernanceError) as exc:
        validate_discord_governance(
            payload=payload,
            principal_role="owner",
            identity_channel_repository=InMemoryIdentityChannelRepository(),
            governance_repository=InMemoryGovernanceRepository(),
        )

    assert exc.value.code == "governance_chat_class_unknown"
    assert "unknown_class" in exc.value.message


def test_unknown_chat_class_with_empty_string() -> None:
    """Edge case: empty string chat_class must also raise DiscordGovernanceError."""
    payload = _build_payload_with_chat_class("")

    with pytest.raises(DiscordGovernanceError) as exc:
        validate_discord_governance(
            payload=payload,
            principal_role="owner",
            identity_channel_repository=InMemoryIdentityChannelRepository(),
            governance_repository=InMemoryGovernanceRepository(),
        )

    assert exc.value.code == "governance_chat_class_unknown"


def test_known_chat_class_does_not_raise() -> None:
    """Regression guard: all valid chat_class values must still pass governance."""
    payload = build_owner_command_request_model(
        action="run_task",
        args=["smoke"],
        actor_id="owner_m11_wp2_003",
        idempotency_key="idem-m11-wp2-003",
        trace_id="trace-m11-wp2-003",
        discord_chat_class="direct",
    )

    result = validate_discord_governance(
        payload=payload,
        principal_role="owner",
        identity_channel_repository=InMemoryIdentityChannelRepository(),
        governance_repository=InMemoryGovernanceRepository(),
    )

    assert result is not None
    assert result.chat_class == "direct"
