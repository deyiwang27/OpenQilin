from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openqilin.control_plane.identity.connector_security import validate_connector_auth
from openqilin.discord_runtime.bridge import (
    DiscordCommandParseError,
    build_discord_ingress_payload,
    format_governed_response,
    parse_actor_role_map,
    parse_discord_command,
)


def test_parse_discord_command_plain_prefix_form() -> None:
    parsed = parse_discord_command("/oq run_task alpha beta", command_prefix="/oq")

    assert parsed is not None
    assert parsed.action == "run_task"
    assert parsed.target is None
    assert parsed.args == ("alpha", "beta")
    assert parsed.recipients == (("runtime", "runtime"),)
    assert parsed.project_id is None
    assert parsed.priority == "normal"


def test_parse_discord_command_json_form() -> None:
    parsed = parse_discord_command(
        '/oq {"action":"msg_send","target":"communication","args":["hello"],'
        '"recipients":[{"recipient_id":"ceo_1","recipient_type":"ceo"}],'
        '"project_id":"project_alpha","priority":"high"}',
        command_prefix="/oq",
    )

    assert parsed is not None
    assert parsed.action == "msg_send"
    assert parsed.target == "communication"
    assert parsed.args == ("hello",)
    assert parsed.recipients == (("ceo_1", "ceo"),)
    assert parsed.project_id == "project_alpha"
    assert parsed.priority == "high"


def test_parse_discord_command_rejects_invalid_json_command() -> None:
    with pytest.raises(DiscordCommandParseError) as error:
        parse_discord_command('/oq {"action":', command_prefix="/oq")
    assert "invalid JSON command body" in error.value.message


def test_build_discord_ingress_payload_generates_valid_signature_headers(monkeypatch) -> None:
    monkeypatch.setenv("OPENQILIN_CONNECTOR_SHARED_SECRET", "test-discord-secret")
    parsed = parse_discord_command("/oq run_task alpha", command_prefix="/oq")
    assert parsed is not None

    payload, signature = build_discord_ingress_payload(
        parsed_command=parsed,
        message_id="discord-msg-001",
        actor_external_id="owner_discord_001",
        actor_role="owner",
        content="/oq run_task alpha",
        guild_id="guild-001",
        channel_id="channel-001",
        channel_type="text",
        chat_class="project",
        connector_shared_secret="test-discord-secret",
        project_id="project-alpha",
        timestamp=datetime(2026, 3, 12, 10, 0, 0, tzinfo=UTC),
        bot_role="ceo",
        bot_id="ceo_core",
        bot_user_id="9001",
    )

    assert payload["raw_payload_hash"]
    assert len(str(payload["raw_payload_hash"])) == 64
    assert signature.startswith("sha256=")
    assert payload["bot_role"] == "ceo"
    assert payload["bot_id"] == "ceo_core"
    assert payload["bot_user_id"] == "9001"
    validate_connector_auth(
        header_channel="discord",
        header_actor_external_id=str(payload["actor_external_id"]),
        header_idempotency_key=str(payload["idempotency_key"]),
        header_signature=signature,
        payload_channel="discord",
        payload_actor_external_id=str(payload["actor_external_id"]),
        payload_idempotency_key=str(payload["idempotency_key"]),
        payload_raw_payload_hash=str(payload["raw_payload_hash"]),
    )


def test_format_governed_response_renders_accepted_and_denied_paths() -> None:
    accepted = format_governed_response(
        status_code=202,
        body={
            "status": "accepted",
            "trace_id": "trace-accepted",
            "data": {"task_id": "task_123", "command": "run_task", "replayed": False},
        },
    )
    denied = format_governed_response(
        status_code=403,
        body={
            "status": "denied",
            "trace_id": "trace-denied",
            "error": {"code": "policy_denied", "message": "policy denied command"},
        },
    )
    assert "[accepted]" in accepted
    assert "task=task_123" in accepted
    assert "[denied]" in denied
    assert "code=policy_denied" in denied


def test_format_governed_response_includes_llm_generated_text_when_available() -> None:
    rendered = format_governed_response(
        status_code=202,
        body={
            "status": "accepted",
            "trace_id": "trace-llm",
            "data": {
                "task_id": "task_llm_1",
                "command": "llm_reason",
                "replayed": False,
                "llm_execution": {
                    "generated_text": "As CEO: Approved. Keep risk under control and report daily.",
                    "recipient_role": "ceo",
                },
            },
        },
    )
    assert "[accepted]" in rendered
    assert "[ceo] As CEO: Approved. Keep risk under control and report daily." in rendered


def test_parse_actor_role_map_ignores_invalid_json() -> None:
    assert parse_actor_role_map("{not-json}") == {}
    assert parse_actor_role_map('{"123":"ceo","456":" project_manager "}') == {
        "123": "ceo",
        "456": "project_manager",
    }
