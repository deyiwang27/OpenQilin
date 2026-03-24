"""M18-WP2 unit tests for @everyone broadcast routing."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.responses import JSONResponse

from openqilin.apps.discord_bot_worker import DiscordBotWorkerConfig, OpenQilinDiscordClient
from openqilin.control_plane.grammar.models import IntentClass
from openqilin.control_plane.routers.discord_ingress import submit_discord_message
from openqilin.control_plane.schemas.discord_ingress import DiscordIngressRequest
from openqilin.control_plane.schemas.owner_commands import OwnerCommandRecipient
from openqilin.discord_runtime.bridge import build_discord_ingress_payload, parse_discord_command


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
    resolved_recipients: tuple[tuple[str, str], ...] | None = None,
) -> tuple[OpenQilinDiscordClient, AsyncMock, AsyncMock]:
    process_event = AsyncMock()
    client = OpenQilinDiscordClient(
        config=_worker_config(bot_role=bot_role, bot_id=bot_id),
        fan_in=cast(Any, SimpleNamespace(process_event=process_event)),
        readiness=cast(Any, MagicMock()),
    )
    cast(Any, client._connection).user = SimpleNamespace(id=user_id)
    resolve_recipients = AsyncMock(return_value=resolved_recipients or ((bot_id, bot_role),))
    setattr(client, "_resolve_recipients", resolve_recipients)
    return client, resolve_recipients, process_event


def _mentioned_user(
    *, user_id: str, bot: bool = True, name: str = "OpenQilin Bot"
) -> SimpleNamespace:
    return SimpleNamespace(id=user_id, bot=bot, display_name=name, name=name)


def _message(
    *,
    content: str,
    mentions: list[SimpleNamespace],
    mention_everyone: bool,
) -> MagicMock:
    channel = MagicMock()
    channel.id = "channel-1"
    channel.name = "leadership-council"
    channel.send = AsyncMock()
    message = MagicMock()
    message.id = "message-1"
    message.content = content
    message.mentions = mentions
    message.mention_everyone = mention_everyone
    message.author = SimpleNamespace(id="owner-1", bot=False)
    message.guild = SimpleNamespace(id="guild-1")
    message.channel = channel
    message.created_at = datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC)
    return message


def _payload(*, bot_role: str, is_everyone_mention: bool) -> DiscordIngressRequest:
    return DiscordIngressRequest(
        trace_id="trace-1",
        external_message_id="discord-message-1",
        actor_external_id="owner-1",
        actor_role="owner",
        idempotency_key="idem-key-12345678",
        raw_payload_hash="a" * 64,
        timestamp=datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC),
        content="What should we focus on this week?",
        action="ask",
        target="sandbox",
        args=["What should we focus on this week?"],
        recipients=[OwnerCommandRecipient(recipient_type="runtime", recipient_id="runtime")],
        guild_id="guild-1",
        channel_id="channel-1",
        channel_type="text",
        chat_class="leadership_council",
        bot_role=bot_role,
        bot_id=f"{bot_role}_core",
        bot_user_id=f"{bot_role}_user",
        is_everyone_mention=is_everyone_mention,
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
            resolve=MagicMock(return_value=SimpleNamespace(target_role="project_manager"))
        ),
        "secretary_agent": MagicMock(),
        "project_manager_agent": MagicMock(),
        "cso_agent": MagicMock(),
        "ceo_agent": MagicMock(),
        "cwo_agent": MagicMock(),
        "auditor_agent": MagicMock(),
        "administrator_agent": MagicMock(),
        "routing_resolver": MagicMock(resolve=MagicMock(return_value=None)),
        "x_openqilin_signature": "sha256=test",
    }


class TestBotWorkerEveryoneGate:
    @pytest.mark.asyncio
    async def test_secretary_does_not_yield_on_everyone_mention(self) -> None:
        client, _resolve_recipients, process_event = _make_client(
            bot_role="secretary",
            bot_id="secretary_core",
            user_id="1001",
        )
        message = _message(
            content="@everyone help us align",
            mentions=[
                _mentioned_user(user_id="1001", name="OpenQilin Secretary"),
                _mentioned_user(user_id="2001", name="OpenQilin CEO"),
            ],
            mention_everyone=True,
        )

        try:
            await client.on_message(message)
        finally:
            await client.close()

        process_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_non_secretary_bot_forwards_on_everyone_mention(self) -> None:
        client, _resolve_recipients, process_event = _make_client(
            bot_role="ceo",
            bot_id="ceo_core",
            user_id="2001",
        )
        message = _message(
            content="@everyone give me guidance",
            mentions=[],
            mention_everyone=True,
        )

        try:
            await client.on_message(message)
        finally:
            await client.close()

        process_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_non_secretary_bot_skips_when_not_mentioned_and_not_everyone(self) -> None:
        client, resolve_recipients, process_event = _make_client(
            bot_role="ceo",
            bot_id="ceo_core",
            user_id="2001",
        )
        message = _message(
            content="Can someone help here?",
            mentions=[],
            mention_everyone=False,
        )

        try:
            await client.on_message(message)
        finally:
            await client.close()

        resolve_recipients.assert_not_awaited()
        process_event.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_is_everyone_mention_set_on_event(self) -> None:
        client, _resolve_recipients, process_event = _make_client(
            bot_role="ceo",
            bot_id="ceo_core",
            user_id="2001",
        )
        message = _message(
            content="@everyone give me guidance",
            mentions=[],
            mention_everyone=True,
        )

        try:
            await client.on_message(message)
        finally:
            await client.close()

        await_args = process_event.await_args
        assert await_args is not None
        event = await_args.args[0]
        assert event.is_everyone_mention is True


class TestBotWorkerExplicitAskRouting:
    @pytest.mark.asyncio
    async def test_targeted_ask_only_named_agent_forwards(self) -> None:
        administrator_client, _resolve_recipients, administrator_process_event = _make_client(
            bot_role="administrator",
            bot_id="administrator_core",
            user_id="3001",
            resolved_recipients=(("runtime", "runtime"),),
        )
        secretary_client, _resolve_recipients, secretary_process_event = _make_client(
            bot_role="secretary",
            bot_id="secretary_core",
            user_id="1001",
            resolved_recipients=(("runtime", "runtime"),),
        )
        message = _message(
            content="/oq ask administrator what is my name?",
            mentions=[],
            mention_everyone=False,
        )

        try:
            await administrator_client.on_message(message)
            await secretary_client.on_message(message)
        finally:
            await administrator_client.close()
            await secretary_client.close()

        administrator_process_event.assert_awaited_once()
        secretary_process_event.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_targeted_secretary_ask_keeps_secretary_as_sender(self) -> None:
        secretary_client, _resolve_recipients, secretary_process_event = _make_client(
            bot_role="secretary",
            bot_id="secretary_core",
            user_id="1001",
            resolved_recipients=(("runtime", "runtime"),),
        )
        ceo_client, _resolve_recipients, ceo_process_event = _make_client(
            bot_role="ceo",
            bot_id="ceo_core",
            user_id="2001",
            resolved_recipients=(("runtime", "runtime"),),
        )
        message = _message(
            content="/oq ask secretary help",
            mentions=[],
            mention_everyone=False,
        )

        try:
            await secretary_client.on_message(message)
            await ceo_client.on_message(message)
        finally:
            await secretary_client.close()
            await ceo_client.close()

        secretary_process_event.assert_awaited_once()
        ceo_process_event.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unrecognized_ask_arg_uses_existing_secretary_fallback(self) -> None:
        secretary_client, _resolve_recipients, secretary_process_event = _make_client(
            bot_role="secretary",
            bot_id="secretary_core",
            user_id="1001",
            resolved_recipients=(("runtime", "runtime"),),
        )
        administrator_client, _resolve_recipients, administrator_process_event = _make_client(
            bot_role="administrator",
            bot_id="administrator_core",
            user_id="3001",
            resolved_recipients=(("runtime", "runtime"),),
        )
        message = _message(
            content="/oq ask about projects",
            mentions=[],
            mention_everyone=False,
        )

        try:
            await secretary_client.on_message(message)
            await administrator_client.on_message(message)
        finally:
            await secretary_client.close()
            await administrator_client.close()

        secretary_process_event.assert_awaited_once()
        administrator_process_event.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_non_ask_explicit_command_uses_existing_secretary_fallback(self) -> None:
        secretary_client, _resolve_recipients, secretary_process_event = _make_client(
            bot_role="secretary",
            bot_id="secretary_core",
            user_id="1001",
            resolved_recipients=(("runtime", "runtime"),),
        )
        administrator_client, _resolve_recipients, administrator_process_event = _make_client(
            bot_role="administrator",
            bot_id="administrator_core",
            user_id="3001",
            resolved_recipients=(("runtime", "runtime"),),
        )
        message = _message(
            content="/oq run_task something",
            mentions=[],
            mention_everyone=False,
        )

        try:
            await secretary_client.on_message(message)
            await administrator_client.on_message(message)
        finally:
            await secretary_client.close()
            await administrator_client.close()

        secretary_process_event.assert_awaited_once()
        administrator_process_event.assert_not_awaited()


class TestIngressEveryoneBroadcast:
    def test_non_secretary_bot_returns_advisory_on_everyone(self) -> None:
        kwargs = _router_kwargs()
        ceo_agent = MagicMock(
            handle_free_text=MagicMock(return_value=SimpleNamespace(advisory_text="CEO advisory"))
        )
        kwargs["ceo_agent"] = ceo_agent

        with patch(
            "openqilin.control_plane.routers.discord_ingress._validate_discord_connector_request",
            return_value=None,
        ):
            response = cast(Any, submit_discord_message)(
                payload=_payload(bot_role="ceo", is_everyone_mention=True),
                **kwargs,
            )

        assert not isinstance(response, JSONResponse)
        assert response.status == "accepted"
        assert response.data.command == "everyone_broadcast"
        assert response.data.llm_execution == {"advisory_response": "CEO advisory"}
        ceo_agent.handle_free_text.assert_called_once()

    def test_secretary_bot_falls_through_on_everyone(self) -> None:
        kwargs = _router_kwargs()
        kwargs["grammar_router"] = MagicMock(
            resolve=MagicMock(return_value=SimpleNamespace(target_role="secretary"))
        )
        secretary_agent = MagicMock(
            handle=MagicMock(
                return_value=SimpleNamespace(
                    advisory_text="Secretary advisory",
                    routing_suggestion=None,
                )
            )
        )
        kwargs["secretary_agent"] = secretary_agent
        ceo_agent = cast(Any, kwargs["ceo_agent"])

        with patch(
            "openqilin.control_plane.routers.discord_ingress._validate_discord_connector_request",
            return_value=None,
        ):
            response = cast(Any, submit_discord_message)(
                payload=_payload(bot_role="secretary", is_everyone_mention=True),
                **kwargs,
            )

        assert not isinstance(response, JSONResponse)
        assert response.status == "accepted"
        assert response.data.dispatch_target == "secretary"
        assert response.data.llm_execution == {
            "advisory_response": "Secretary advisory",
            "routing_suggestion": None,
        }
        secretary_agent.handle.assert_called_once()
        ceo_agent.handle_free_text.assert_not_called()

    def test_advisory_failure_returns_fallback_not_500(self) -> None:
        kwargs = _router_kwargs()
        kwargs["ceo_agent"] = MagicMock(
            handle_free_text=MagicMock(side_effect=RuntimeError("boom"))
        )

        with patch(
            "openqilin.control_plane.routers.discord_ingress._validate_discord_connector_request",
            return_value=None,
        ):
            response = cast(Any, submit_discord_message)(
                payload=_payload(bot_role="ceo", is_everyone_mention=True),
                **kwargs,
            )

        assert not isinstance(response, JSONResponse)
        assert response.status == "accepted"
        assert response.data.command == "everyone_broadcast"
        assert (
            response.data.llm_execution["advisory_response"]
            == "I'm the Ceo agent. I'm unable to respond right now — please try again."
        )


def test_build_discord_ingress_payload_passes_is_everyone_mention() -> None:
    parsed = parse_discord_command("/oq ask status", command_prefix="/oq")
    assert parsed is not None

    payload, _signature = build_discord_ingress_payload(
        parsed_command=parsed,
        message_id="discord-msg-001",
        actor_external_id="owner-1",
        actor_role="owner",
        content="@everyone status",
        guild_id="guild-1",
        channel_id="channel-1",
        channel_type="text",
        chat_class="leadership_council",
        connector_shared_secret="test-secret",
        bot_role="ceo",
        bot_id="ceo_core",
        bot_user_id="2001",
        is_everyone_mention=True,
    )

    assert payload["is_everyone_mention"] is True
