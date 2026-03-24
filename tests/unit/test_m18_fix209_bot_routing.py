"""Regression tests for issue #209 Tier 1 bot routing behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openqilin.apps.discord_bot_worker import DiscordBotWorkerConfig, OpenQilinDiscordClient
from openqilin.control_plane.advisory.topic_router import RoutingDecision
from openqilin.control_plane.grammar.models import IntentClass
from openqilin.control_plane.routers.discord_ingress import submit_discord_message
from openqilin.control_plane.schemas.discord_ingress import DiscordIngressRequest
from openqilin.control_plane.schemas.owner_commands import OwnerCommandRecipient


def _worker_config(*, bot_role: str, bot_id: str) -> DiscordBotWorkerConfig:
    return DiscordBotWorkerConfig(
        bot_role=bot_role,
        bot_id=bot_id,
        token="discord-token",
        control_plane_base_url="http://control-plane:8000",
        connector_shared_secret="secret",
        command_prefix="/oq",
        actor_role_default="owner",
        actor_role_map={},
        allowed_guild_ids=frozenset(),
        allowed_channel_ids=frozenset(),
        request_timeout_seconds=5.0,
        response_chunk_size_chars=1900,
        response_retry_attempts=2,
        response_retry_base_delay_seconds=0.1,
    )


def _make_client(
    *,
    bot_role: str,
    bot_id: str,
    user_id: str,
    topic_decision: RoutingDecision | None,
    resolved_recipients: tuple[tuple[str, str], ...] | None = None,
) -> tuple[OpenQilinDiscordClient, AsyncMock, AsyncMock]:
    process_event = AsyncMock()
    client = OpenQilinDiscordClient(
        config=_worker_config(bot_role=bot_role, bot_id=bot_id),
        fan_in=cast(Any, SimpleNamespace(process_event=process_event)),
        readiness=cast(Any, MagicMock()),
    )
    cast(Any, client._connection).user = SimpleNamespace(id=user_id)
    client._topic_router = MagicMock(classify=MagicMock(return_value=topic_decision))
    resolve_recipients = AsyncMock(return_value=resolved_recipients or ((bot_id, bot_role),))
    setattr(client, "_resolve_recipients", resolve_recipients)
    return client, resolve_recipients, process_event


def _message(
    *,
    content: str,
    channel_name: str,
    mentions: list[SimpleNamespace] | None = None,
    mention_everyone: bool = False,
) -> MagicMock:
    channel = MagicMock()
    channel.id = "channel-1"
    channel.name = channel_name
    channel.send = AsyncMock()
    message = MagicMock()
    message.id = "message-1"
    message.content = content
    message.mentions = mentions or []
    message.mention_everyone = mention_everyone
    message.author = SimpleNamespace(id="owner-1", bot=False)
    message.guild = SimpleNamespace(id="guild-1")
    message.channel = channel
    message.created_at = datetime(2026, 3, 24, 10, 0, 0, tzinfo=UTC)
    return message


def _payload(*, bot_role: str) -> DiscordIngressRequest:
    return DiscordIngressRequest(
        trace_id="trace-1",
        external_message_id="discord-message-1",
        actor_external_id="owner-1",
        actor_role="owner",
        idempotency_key="idem-key-12345678",
        raw_payload_hash="a" * 64,
        timestamp=datetime(2026, 3, 24, 10, 0, 0, tzinfo=UTC),
        content="what is my budget status?",
        action="ask",
        target="sandbox",
        args=["what is my budget status?"],
        recipients=[OwnerCommandRecipient(recipient_type="runtime", recipient_id="runtime")],
        guild_id="guild-1",
        channel_id="channel-1",
        channel_type="text",
        chat_class="governance",
        bot_role=bot_role,
        bot_id=f"{bot_role}_core",
        bot_user_id=f"{bot_role}_user",
        is_everyone_mention=False,
    )


def _router_kwargs() -> dict[str, Any]:
    return {
        "request": MagicMock(),
        "admission_service": MagicMock(),
        "policy_runtime_client": MagicMock(),
        "budget_reservation_service": MagicMock(),
        "runtime_state_repo": MagicMock(),
        "task_dispatch_service": MagicMock(),
        "tracer": MagicMock(),
        "audit_writer": MagicMock(),
        "metric_recorder": MagicMock(),
        "governance_repository": MagicMock(),
        "identity_channel_repository": MagicMock(),
        "binding_service": MagicMock(),
        "grammar_classifier": MagicMock(classify=MagicMock(return_value=IntentClass.DISCUSSION)),
        "grammar_parser": MagicMock(),
        "grammar_router": MagicMock(
            resolve=MagicMock(return_value=SimpleNamespace(target_role="secretary"))
        ),
        "secretary_agent": MagicMock(
            handle=MagicMock(
                return_value=SimpleNamespace(
                    advisory_text="Secretary advisory",
                    routing_suggestion=None,
                )
            )
        ),
        "project_manager_agent": MagicMock(),
        "cso_agent": MagicMock(),
        "ceo_agent": MagicMock(),
        "cwo_agent": MagicMock(),
        "auditor_agent": MagicMock(),
        "administrator_agent": MagicMock(),
        "routing_resolver": MagicMock(resolve=MagicMock(return_value=None)),
        "advisory_topic_router": MagicMock(classify=MagicMock(return_value=None)),
        "bot_registry_reader": MagicMock(get_mention=MagicMock(return_value=None)),
        "x_openqilin_signature": "sha256=test",
    }


@pytest.mark.asyncio
async def test_bot_worker_tier1_auditor_role_forwards() -> None:
    client, resolve_recipients, process_event = _make_client(
        bot_role="auditor",
        bot_id="auditor_core",
        user_id="2001",
        topic_decision=RoutingDecision("auditor", "high"),
        resolved_recipients=(("runtime", "runtime"),),
    )
    message = _message(content="what is my budget status?", channel_name="governance")

    try:
        await client.on_message(message)
    finally:
        await client.close()

    resolve_recipients.assert_awaited_once()
    process_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_bot_worker_tier1_secretary_skips_for_auditor() -> None:
    client, resolve_recipients, process_event = _make_client(
        bot_role="secretary",
        bot_id="secretary_core",
        user_id="1001",
        topic_decision=RoutingDecision("auditor", "high"),
        resolved_recipients=(("runtime", "runtime"),),
    )
    message = _message(content="what is my budget status?", channel_name="governance")

    try:
        await client.on_message(message)
    finally:
        await client.close()

    resolve_recipients.assert_not_awaited()
    process_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_bot_worker_tier1_restricted_in_project_channel() -> None:
    client, resolve_recipients, process_event = _make_client(
        bot_role="secretary",
        bot_id="secretary_core",
        user_id="1001",
        topic_decision=RoutingDecision("auditor", "high"),
        resolved_recipients=(("runtime", "runtime"),),
    )
    message = _message(content="what is my budget status?", channel_name="project-apollo")

    try:
        await client.on_message(message)
    finally:
        await client.close()

    resolve_recipients.assert_awaited_once()
    process_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_bot_worker_tier1_no_match_secretary_handles() -> None:
    client, resolve_recipients, process_event = _make_client(
        bot_role="secretary",
        bot_id="secretary_core",
        user_id="1001",
        topic_decision=None,
        resolved_recipients=(("runtime", "runtime"),),
    )
    message = _message(content="can someone help here?", channel_name="governance")

    try:
        await client.on_message(message)
    finally:
        await client.close()

    resolve_recipients.assert_awaited_once()
    process_event.assert_awaited_once()


def test_ingress_tier1_forwarded_auditor_dispatches() -> None:
    kwargs = _router_kwargs()
    auditor_agent = MagicMock(
        handle_free_text=MagicMock(return_value=SimpleNamespace(advisory_text="Auditor advisory"))
    )
    kwargs["auditor_agent"] = auditor_agent

    with patch(
        "openqilin.control_plane.routers.discord_ingress._validate_discord_connector_request",
        return_value=None,
    ):
        response = cast(Any, submit_discord_message)(
            payload=_payload(bot_role="auditor"),
            **kwargs,
        )

    assert response.data.command == "ask"
    assert response.data.llm_execution == {"advisory_response": "Auditor advisory"}
    auditor_agent.handle_free_text.assert_called_once()
