from __future__ import annotations

from pathlib import Path
import re


def _extract_compose_service_block(compose_text: str, service_name: str) -> str | None:
    pattern = re.compile(
        rf"(?ms)^  {re.escape(service_name)}:\n(?P<body>(?:    .*\n)+?)(?=^  [a-zA-Z0-9_]+:|\Z)"
    )
    match = pattern.search(compose_text)
    if match is None:
        return None
    return match.group("body")


def test_m9_wp2_discord_worker_is_wired_in_full_profile_compose() -> None:
    project_root = Path(__file__).resolve().parents[2]
    compose_text = (project_root / "compose.yml").read_text(encoding="utf-8")
    discord_block = _extract_compose_service_block(compose_text, "discord_bot_worker")
    assert discord_block is not None
    assert 'profiles: ["full"]' in discord_block
    assert "python -m openqilin.apps.discord_bot_worker" in discord_block
    assert "OPENQILIN_DISCORD_BOT_TOKEN" in discord_block
    assert "OPENQILIN_DISCORD_CONTROL_PLANE_BASE_URL" in discord_block
    assert "OPENQILIN_DISCORD_ALLOWED_GUILD_IDS_CSV" in discord_block
    assert "OPENQILIN_DISCORD_ALLOWED_CHANNEL_IDS_CSV" in discord_block
    assert "OPENQILIN_CONNECTOR_SHARED_SECRET" in discord_block
    assert "openqilin.discord_bot_worker.ready" in discord_block


def test_m9_wp2_env_template_exposes_discord_runtime_settings() -> None:
    project_root = Path(__file__).resolve().parents[2]
    env_text = (project_root / ".env.example").read_text(encoding="utf-8")
    assert "OPENQILIN_DISCORD_BOT_TOKEN" in env_text
    assert "OPENQILIN_DISCORD_CONTROL_PLANE_BASE_URL" in env_text
    assert "OPENQILIN_DISCORD_COMMAND_PREFIX" in env_text
    assert "OPENQILIN_DISCORD_ACTOR_ROLE_MAP_JSON" in env_text
    assert "OPENQILIN_DISCORD_ALLOWED_GUILD_IDS_CSV" in env_text
    assert "OPENQILIN_DISCORD_ALLOWED_CHANNEL_IDS_CSV" in env_text
