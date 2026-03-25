"""Regression tests for Secretary absent-bot Tier 1 referrals."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from openqilin.apps.discord_bot_worker import (
    DiscordBotWorkerConfig,
    DiscordRoleBotReadiness,
    OpenQilinDiscordClient,
)
from openqilin.control_plane.advisory.topic_router import RoutingDecision


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
    topic_role: str | None,
    readiness: Any | None = None,
    redis_client: Any | None = None,
) -> tuple[OpenQilinDiscordClient, Any, AsyncMock, AsyncMock]:
    process_event = AsyncMock()
    readiness_mock = readiness or MagicMock()
    client = OpenQilinDiscordClient(
        config=_worker_config(bot_role=bot_role, bot_id=bot_id),
        fan_in=cast(Any, SimpleNamespace(process_event=process_event)),
        readiness=cast(Any, readiness_mock),
        redis_client=redis_client,
    )
    cast(Any, client._connection).user = SimpleNamespace(id=user_id)
    topic_decision = RoutingDecision(topic_role, "high") if topic_role is not None else None
    client._topic_router = MagicMock(classify=MagicMock(return_value=topic_decision))
    resolve_recipients = AsyncMock(return_value=((bot_id, bot_role),))
    setattr(client, "_resolve_recipients", resolve_recipients)
    return client, readiness_mock, resolve_recipients, process_event


def _message() -> MagicMock:
    channel = MagicMock()
    channel.id = "channel-1"
    channel.name = "governance"
    channel.send = AsyncMock()
    guild = MagicMock()
    guild.id = "guild-1"
    guild.get_member = MagicMock()
    message = MagicMock()
    message.id = "message-1"
    message.content = "what is my budget status?"
    message.mentions = []
    message.mention_everyone = False
    message.author = SimpleNamespace(id="owner-1", bot=False)
    message.guild = guild
    message.channel = channel
    message.created_at = datetime(2026, 3, 24, 10, 0, 0, tzinfo=UTC)
    return message


@pytest.mark.asyncio
async def test_readiness_get_user_id_returns_id_when_ready(tmp_path: Path) -> None:
    readiness = DiscordRoleBotReadiness(
        required_roles=frozenset({"auditor"}),
        bot_id_by_role={"auditor": "auditor_core"},
        marker_path=tmp_path / "ready.marker",
    )

    await readiness.mark_ready(role="auditor", user_id="123")

    assert readiness.get_user_id("auditor") == "123"


def test_readiness_get_user_id_returns_none_when_not_ready(tmp_path: Path) -> None:
    readiness = DiscordRoleBotReadiness(
        required_roles=frozenset({"auditor"}),
        bot_id_by_role={"auditor": "auditor_core"},
        marker_path=tmp_path / "ready.marker",
    )

    assert readiness.get_user_id("auditor") is None


@pytest.mark.asyncio
async def test_readiness_get_user_id_returns_none_after_mark_offline(tmp_path: Path) -> None:
    readiness = DiscordRoleBotReadiness(
        required_roles=frozenset({"auditor"}),
        bot_id_by_role={"auditor": "auditor_core"},
        marker_path=tmp_path / "ready.marker",
    )
    await readiness.mark_ready(role="auditor", user_id="123")

    await readiness.mark_offline(role="auditor")

    assert readiness.get_user_id("auditor") is None


@pytest.mark.asyncio
async def test_secretary_posts_referral_when_matched_bot_user_id_unknown() -> None:
    readiness = MagicMock()
    readiness.get_user_id = MagicMock(return_value=None)
    client, _readiness, resolve_recipients, process_event = _make_client(
        bot_role="secretary",
        bot_id="secretary_core",
        user_id="1001",
        topic_role="auditor",
        readiness=readiness,
    )
    message = _message()

    try:
        await client.on_message(message)
    finally:
        await client.close()

    readiness.get_user_id.assert_called_once_with("auditor")
    resolve_recipients.assert_not_awaited()
    process_event.assert_not_awaited()
    message.guild.get_member.assert_not_called()
    message.channel.send.assert_awaited_once_with(
        "The **Auditor** agent handles that topic but isn't available in this channel. "
        "Try `/oq ask auditor <question>` in a channel where they're active."
    )


@pytest.mark.asyncio
async def test_secretary_defers_when_bot_found_via_redis() -> None:
    readiness = MagicMock()
    readiness.get_user_id = MagicMock(return_value=None)
    redis_client = MagicMock()
    redis_client.hget = MagicMock(
        return_value=b"2001",
    )
    client, _readiness, resolve_recipients, process_event = _make_client(
        bot_role="secretary",
        bot_id="secretary_core",
        user_id="1001",
        topic_role="auditor",
        readiness=readiness,
        redis_client=redis_client,
    )
    message = _message()

    try:
        await client.on_message(message)
    finally:
        await client.close()

    readiness.get_user_id.assert_called_once_with("auditor")
    redis_client.hget.assert_called_once_with("openqilin:bot_discord_ids", "auditor")
    message.guild.get_member.assert_not_called()
    resolve_recipients.assert_not_awaited()
    process_event.assert_not_awaited()
    message.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_secretary_skips_when_agent_bot_mentioned_via_registry() -> None:
    redis_client = MagicMock()
    redis_client.hgetall = MagicMock(return_value={b"ceo": b"999"})
    client, _readiness, resolve_recipients, process_event = _make_client(
        bot_role="secretary",
        bot_id="secretary_core",
        user_id="1001",
        topic_role=None,
        redis_client=redis_client,
    )
    message = _message()
    message.mentions = [SimpleNamespace(id="999", bot=False)]
    message.content = "<@999> can you weigh in on this?"

    try:
        await client.on_message(message)
    finally:
        await client.close()

    redis_client.hgetall.assert_called_once_with("openqilin:bot_discord_ids")
    resolve_recipients.assert_not_awaited()
    process_event.assert_not_awaited()
    message.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_secretary_defers_when_bot_present() -> None:
    readiness = MagicMock()
    readiness.get_user_id = MagicMock(return_value="2002")
    client, _readiness, resolve_recipients, process_event = _make_client(
        bot_role="secretary",
        bot_id="secretary_core",
        user_id="1001",
        topic_role="auditor",
        readiness=readiness,
    )
    message = _message()

    try:
        await client.on_message(message)
    finally:
        await client.close()

    readiness.get_user_id.assert_called_once_with("auditor")
    message.guild.get_member.assert_not_called()
    resolve_recipients.assert_not_awaited()
    process_event.assert_not_awaited()
    message.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_secretary_defers_when_matched_bot_user_id_is_string() -> None:
    readiness = MagicMock()
    readiness.get_user_id = MagicMock(return_value="2002")
    client, _readiness, resolve_recipients, process_event = _make_client(
        bot_role="secretary",
        bot_id="secretary_core",
        user_id="1001",
        topic_role="auditor",
        readiness=readiness,
    )
    message = _message()

    try:
        await client.on_message(message)
    finally:
        await client.close()

    readiness.get_user_id.assert_called_once_with("auditor")
    message.guild.get_member.assert_not_called()
    resolve_recipients.assert_not_awaited()
    process_event.assert_not_awaited()
    message.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_secretary_bot_always_returns_regardless_of_matched_bot_presence() -> None:
    readiness = MagicMock()
    readiness.get_user_id = MagicMock(return_value="3003")
    client, _readiness, resolve_recipients, process_event = _make_client(
        bot_role="auditor",
        bot_id="auditor_core",
        user_id="2001",
        topic_role="administrator",
        readiness=readiness,
    )
    message = _message()

    try:
        await client.on_message(message)
    finally:
        await client.close()

    readiness.get_user_id.assert_not_called()
    message.guild.get_member.assert_not_called()
    resolve_recipients.assert_not_awaited()
    process_event.assert_not_awaited()
    message.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_referral_message_format_project_manager_role() -> None:
    readiness = MagicMock()
    readiness.get_user_id = MagicMock(return_value=None)
    client, _readiness, resolve_recipients, process_event = _make_client(
        bot_role="secretary",
        bot_id="secretary_core",
        user_id="1001",
        topic_role="project_manager",
        readiness=readiness,
    )
    message = _message()

    try:
        await client.on_message(message)
    finally:
        await client.close()

    resolve_recipients.assert_not_awaited()
    process_event.assert_not_awaited()
    message.channel.send.assert_awaited_once_with(
        "The **Project Manager** agent handles that topic but isn't available in this "
        "channel. Try `/oq ask project_manager <question>` in a channel where they're "
        "active."
    )
