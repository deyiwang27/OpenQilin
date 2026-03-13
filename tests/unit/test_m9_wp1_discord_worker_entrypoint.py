from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from openqilin.apps import discord_bot_worker as discord_worker_module
from openqilin.apps.discord_bot_worker import build_worker_config, main
from openqilin.shared_kernel.config import RuntimeSettings


def test_m9_wp1_discord_worker_run_once_emits_ready_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "discord-worker.ready"
    monkeypatch.setattr(discord_worker_module, "READY_MARKER_PATH", marker)

    asyncio.run(main(run_once=True))

    assert marker.exists()
    assert marker.read_text(encoding="utf-8").strip() == "ready"


def test_m9_wp1_build_worker_config_uses_runtime_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENQILIN_DISCORD_BOT_TOKEN", "token-from-env")
    settings = RuntimeSettings(
        discord_control_plane_base_url="http://api_app:8000",
        discord_command_prefix="/oq",
        discord_actor_role_default="owner",
        discord_actor_role_map_json='{"100":"ceo"}',
        discord_allowed_guild_ids_csv="1,2",
        discord_allowed_channel_ids_csv="10,20",
        connector_shared_secret="secret-1",
    )

    config = build_worker_config(settings)

    assert config.bot_role == "runtime_agent"
    assert config.bot_id == "runtime_agent"
    assert config.token == "token-from-env"
    assert config.control_plane_base_url == "http://api_app:8000"
    assert config.command_prefix == "/oq"
    assert config.actor_role_default == "owner"
    assert config.actor_role_map == {"100": "ceo"}
    assert config.allowed_guild_ids == frozenset({"1", "2"})
    assert config.allowed_channel_ids == frozenset({"10", "20"})
    assert config.connector_shared_secret == "secret-1"


def test_m9_wp1_build_worker_config_multi_bot_resolves_worker_role_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENQILIN_DISCORD_BOT_TOKEN", raising=False)
    settings = RuntimeSettings(
        discord_multi_bot_enabled=True,
        discord_worker_role="ceo",
        discord_required_role_bots_csv="ceo",
        discord_role_bot_tokens_json=(
            '{"ceo":{"token":"ceo-token","bot_id":"ceo_core","guild_allowlist":["1","2"]}}'
        ),
        discord_allowed_guild_ids_csv="2,3",
        connector_shared_secret="secret-1",
    )

    config = build_worker_config(settings)

    assert config.bot_role == "ceo"
    assert config.bot_id == "ceo_core"
    assert config.token == "ceo-token"
    assert config.allowed_guild_ids == frozenset({"2"})


def test_m9_wp1_build_worker_config_rejects_missing_worker_role_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENQILIN_DISCORD_BOT_TOKEN", raising=False)
    settings = RuntimeSettings(
        discord_multi_bot_enabled=True,
        discord_worker_role="ceo",
        discord_required_role_bots_csv="ceo",
        discord_role_bot_tokens_json='{"administrator":"admin-token"}',
    )

    with pytest.raises(RuntimeError) as error:
        build_worker_config(settings)

    assert "missing required role-bot tokens: ceo" in str(error.value)


def test_m9_wp1_build_worker_config_rejects_empty_single_bot_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENQILIN_DISCORD_BOT_TOKEN", raising=False)
    settings = RuntimeSettings(
        discord_multi_bot_enabled=False,
        discord_bot_token=None,
        discord_role_bot_tokens_json="{}",
    )

    with pytest.raises(RuntimeError) as error:
        build_worker_config(settings)

    assert "discord_role_bot_registry_empty" in str(error.value)
