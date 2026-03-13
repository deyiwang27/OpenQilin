from __future__ import annotations

from datetime import UTC, datetime
import json
import re

import httpx
import pytest
import respx

from openqilin.apps.discord_bot_worker import (
    DiscordInboundEvent,
    DiscordIngressFanIn,
    _chunk_discord_message,
    _ordered_recipient_roles,
)
from openqilin.discord_runtime.bridge import parse_discord_command


class _FakeSendError(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(f"send failed: {status}")
        self.status = status


class _FlakyChannel:
    def __init__(self, *, fail_count: int, fail_status: int = 429) -> None:
        self._remaining_failures = fail_count
        self._fail_status = fail_status
        self.calls = 0
        self.sent_messages: list[str] = []

    async def send(self, message: str) -> None:
        self.calls += 1
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise _FakeSendError(self._fail_status)
        self.sent_messages.append(message)


def test_m10_wp5_chunking_preserves_full_text_without_truncation() -> None:
    text = "A" * 4800
    chunks = _chunk_discord_message(text, max_chunk_chars=500)

    assert len(chunks) > 1
    assert all(len(chunk) <= 500 for chunk in chunks)
    assert "".join(chunks) == text


@pytest.mark.asyncio
async def test_m10_wp5_delivery_retry_handles_transient_error() -> None:
    fan_in = DiscordIngressFanIn(
        control_plane_base_url="http://control-plane:8000",
        connector_shared_secret="secret",
        request_timeout_seconds=5.0,
        response_chunk_size_chars=1900,
        response_retry_attempts=2,
        response_retry_base_delay_seconds=0.01,
    )
    channel = _FlakyChannel(fail_count=1, fail_status=429)
    try:
        await fan_in._send_with_retry(channel=channel, message="hello")
    finally:
        await fan_in.close()

    assert channel.calls == 2
    assert channel.sent_messages == ["hello"]


@pytest.mark.asyncio
async def test_m10_wp5_delivery_retry_does_not_retry_permanent_error() -> None:
    fan_in = DiscordIngressFanIn(
        control_plane_base_url="http://control-plane:8000",
        connector_shared_secret="secret",
        request_timeout_seconds=5.0,
        response_chunk_size_chars=1900,
        response_retry_attempts=2,
        response_retry_base_delay_seconds=0.01,
    )
    channel = _FlakyChannel(fail_count=1, fail_status=403)
    with pytest.raises(_FakeSendError):
        try:
            await fan_in._send_with_retry(channel=channel, message="hello")
        finally:
            await fan_in.close()

    assert channel.calls == 1


@pytest.mark.asyncio
@respx.mock
async def test_m10_wp5_process_event_sends_chunked_multipart_response() -> None:
    route = respx.post("http://control-plane:8000/v1/connectors/discord/messages").mock(
        return_value=httpx.Response(
            202,
            json={
                "status": "accepted",
                "trace_id": "trace-wp5",
                "data": {
                    "task_id": "task-wp5",
                    "command": "llm_reason",
                    "replayed": False,
                    "llm_execution": {
                        "recipient_role": "ceo",
                        "generated_text": "X" * 4200,
                    },
                },
            },
        )
    )
    parsed = parse_discord_command(
        '/oq {"action":"llm_reason","target":"llm","args":["status"],'
        '"recipients":[{"recipient_id":"ceo_core","recipient_type":"ceo"}]}',
        command_prefix="/oq",
    )
    assert parsed is not None
    channel = _FlakyChannel(fail_count=0)
    fan_in = DiscordIngressFanIn(
        control_plane_base_url="http://control-plane:8000",
        connector_shared_secret="secret",
        request_timeout_seconds=5.0,
        response_chunk_size_chars=600,
        response_retry_attempts=2,
        response_retry_base_delay_seconds=0.01,
    )
    event = DiscordInboundEvent(
        bot_role="ceo",
        bot_id="ceo_core",
        bot_user_id="2001",
        parsed_command=parsed,
        message_id="msg-wp5",
        actor_external_id="owner-1",
        actor_role="owner",
        content="/oq llm_reason status",
        guild_id="guild-1",
        channel_id="channel-1",
        channel_type="text",
        chat_class="project",
        project_id="project_alpha",
        timestamp=datetime(2026, 3, 13, 2, 30, 0, tzinfo=UTC),
        response_channel=channel,
    )
    try:
        await fan_in.process_event(event)
    finally:
        await fan_in.close()

    assert route.called
    payload = json.loads(route.calls[0].request.content.decode("utf-8"))
    assert payload["bot_role"] == "ceo"
    assert len(channel.sent_messages) > 1
    reassembled = "".join(
        re.sub(r"^\[ceo \d+/\d+\] ", "", chunk) for chunk in channel.sent_messages
    )
    assert "X" * 4200 in reassembled


def test_m10_wp5_recipient_role_order_is_deterministic() -> None:
    roles = _ordered_recipient_roles(
        recipients=(("ceo_core", "ceo"), ("auditor_core", "auditor"), ("cwo_core", "cwo")),
        fallback_role="ceo",
    )

    assert roles == ("auditor", "ceo", "cwo")
