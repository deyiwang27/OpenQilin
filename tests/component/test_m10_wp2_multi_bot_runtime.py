from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import httpx
import pytest
import respx

from openqilin.apps.discord_bot_worker import (
    DiscordInboundEvent,
    DiscordIngressFanIn,
    DiscordRoleBotReadiness,
    build_worker_launch_plan,
)
from openqilin.discord_runtime.bridge import parse_discord_command
from openqilin.shared_kernel.config import RuntimeSettings


class _FakeChannel:
    def __init__(self) -> None:
        self.sent_messages: list[str] = []

    async def send(self, message: str) -> None:
        self.sent_messages.append(message)


@pytest.mark.asyncio
async def test_m10_wp2_readiness_tracks_required_role_bots(tmp_path: Path) -> None:
    marker = tmp_path / "discord-worker.ready"
    tracker = DiscordRoleBotReadiness(
        required_roles=frozenset({"ceo", "auditor"}),
        bot_id_by_role={"ceo": "ceo_core", "auditor": "auditor_core"},
        marker_path=marker,
    )

    await tracker.mark_ready(role="ceo", user_id="1001")
    assert tracker.is_healthy is False
    assert not marker.exists()

    await tracker.mark_ready(role="auditor", user_id="1002")
    assert tracker.is_healthy is True
    assert marker.exists()

    await tracker.mark_offline(role="ceo")
    assert tracker.is_healthy is False
    assert not marker.exists()


@pytest.mark.asyncio
@respx.mock
async def test_m10_wp2_event_fan_in_emits_bot_identity_context() -> None:
    route = respx.post("http://control-plane:8000/v1/connectors/discord/messages").mock(
        return_value=httpx.Response(
            202,
            json={
                "status": "accepted",
                "trace_id": "trace-m10-wp2",
                "data": {
                    "task_id": "task-1",
                    "command": "run_task",
                    "replayed": False,
                },
            },
        )
    )
    fan_in = DiscordIngressFanIn(
        control_plane_base_url="http://control-plane:8000",
        connector_shared_secret="secret-1",
        request_timeout_seconds=5.0,
        response_chunk_size_chars=1900,
        response_retry_attempts=2,
        response_retry_base_delay_seconds=0.1,
    )
    parsed = parse_discord_command("/oq run_task alpha", command_prefix="/oq")
    assert parsed is not None
    channel = _FakeChannel()
    event = DiscordInboundEvent(
        bot_role="ceo",
        bot_id="ceo_core",
        bot_user_id="2001",
        parsed_command=parsed,
        message_id="msg-1",
        actor_external_id="owner-1",
        actor_role="owner",
        content="/oq run_task alpha",
        guild_id="guild-1",
        channel_id="channel-1",
        channel_type="text",
        chat_class="project",
        project_id="project_alpha",
        timestamp=datetime(2026, 3, 13, 2, 0, 0, tzinfo=UTC),
        response_channel=channel,
    )
    try:
        await fan_in.process_event(event)
    finally:
        await fan_in.close()

    assert route.called
    request_payload = json.loads(route.calls[0].request.content.decode("utf-8"))
    assert request_payload["bot_role"] == "ceo"
    assert request_payload["bot_id"] == "ceo_core"
    assert request_payload["bot_user_id"] == "2001"
    assert channel.sent_messages
    assert channel.sent_messages[0].startswith("[accepted]")


def test_m10_wp2_build_worker_launch_plan_multi_bot_includes_all_active_roles() -> None:
    settings = RuntimeSettings(
        discord_multi_bot_enabled=True,
        discord_required_role_bots_csv="ceo,auditor",
        discord_role_bot_tokens_json=(
            '{"ceo":{"token":"ceo-token","bot_id":"ceo_core"},'
            '"auditor":{"token":"auditor-token"},'
            '"project_manager":{"token":"pm-token","status":"disabled"}}'
        ),
    )

    launch_plan = build_worker_launch_plan(settings)

    assert launch_plan.required_roles == frozenset({"ceo", "auditor"})
    assert [config.bot_role for config in launch_plan.configs] == ["auditor", "ceo"]
