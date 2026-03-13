"""Async entrypoint for the OpenQilin real Discord bot worker."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import discord
import httpx
import structlog

from openqilin.discord_runtime.bridge import (
    DiscordCommandParseError,
    build_discord_ingress_payload,
    format_governed_response,
    parse_actor_role_map,
    parse_discord_command,
)
from openqilin.shared_kernel.config import RuntimeSettings
from openqilin.shared_kernel.startup_validation import enforce_connector_secret_hardening

LOGGER = structlog.get_logger(__name__)
READY_MARKER_PATH = Path("/tmp/openqilin.discord_bot_worker.ready")


def _mark_ready() -> None:
    """Emit deterministic ready marker for container health checks."""

    READY_MARKER_PATH.write_text("ready\n", encoding="utf-8")


@dataclass(frozen=True, slots=True)
class DiscordBotWorkerConfig:
    """Runtime configuration for Discord bot ingress bridge."""

    token: str
    control_plane_base_url: str
    connector_shared_secret: str
    command_prefix: str
    actor_role_default: str
    actor_role_map: dict[str, str]
    allowed_guild_ids: frozenset[str]
    allowed_channel_ids: frozenset[str]
    request_timeout_seconds: float


def _channel_type_name(channel: Any) -> str:
    if isinstance(channel, discord.DMChannel):
        return "dm"
    if isinstance(channel, discord.GroupChannel):
        return "group"
    if isinstance(channel, discord.Thread):
        return "thread"
    return "text"


def _resolve_chat_class(channel: Any) -> str:
    if isinstance(channel, (discord.DMChannel, discord.GroupChannel)):
        return "direct"
    channel_name = getattr(channel, "name", "")
    normalized = str(channel_name).strip().lower().replace("-", "_")
    if normalized == "leadership_council":
        return "leadership_council"
    if normalized == "governance":
        return "governance"
    if normalized == "executive":
        return "executive"
    return "project"


def _derive_project_id(channel: Any) -> str | None:
    channel_name = str(getattr(channel, "name", "")).strip().lower()
    if not channel_name:
        return None
    base = channel_name
    if base.startswith("project-"):
        base = base[len("project-") :]
    elif base.startswith("project_"):
        base = base[len("project_") :]
    normalized = "".join(
        character if character.isalnum() or character in {"_", "-"} else "_" for character in base
    ).replace("-", "_")
    normalized = normalized.strip("_")
    return normalized or None


def _parse_id_allowlist(raw_value: str) -> frozenset[str]:
    normalized = tuple(
        item.strip() for item in raw_value.split(",") if item is not None and item.strip()
    )
    return frozenset(normalized)


class OpenQilinDiscordClient(discord.Client):
    """Discord gateway client that bridges inbound messages to governed ingress."""

    def __init__(self, *, config: DiscordBotWorkerConfig) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self._config = config
        self._http_client = httpx.AsyncClient(timeout=config.request_timeout_seconds)
        self._ingress_url = (
            f"{self._config.control_plane_base_url.rstrip('/')}/v1/connectors/discord/messages"
        )

    async def close(self) -> None:
        await self._http_client.aclose()
        await super().close()

    async def on_ready(self) -> None:
        _mark_ready()
        LOGGER.info(
            "discord.worker.ready",
            bot_user=str(self.user),
            control_plane_base_url=self._config.control_plane_base_url,
        )

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        guild_id = str(message.guild.id) if message.guild is not None else "dm"
        channel_id = str(message.channel.id)
        if (
            len(self._config.allowed_guild_ids) > 0
            and guild_id not in self._config.allowed_guild_ids
        ):
            LOGGER.info(
                "discord.worker.message_ignored",
                reason="guild_not_allowlisted",
                guild_id=guild_id,
                channel_id=channel_id,
                message_id=str(message.id),
            )
            return
        if (
            len(self._config.allowed_channel_ids) > 0
            and channel_id not in self._config.allowed_channel_ids
        ):
            LOGGER.info(
                "discord.worker.message_ignored",
                reason="channel_not_allowlisted",
                guild_id=guild_id,
                channel_id=channel_id,
                message_id=str(message.id),
            )
            return
        try:
            parsed = parse_discord_command(
                message.content,
                command_prefix=self._config.command_prefix,
            )
        except DiscordCommandParseError as error:
            await message.channel.send(
                f"[error] code=discord_command_parse_error message={error.message}"
            )
            return
        if parsed is None:
            return
        actor_id = str(message.author.id)
        actor_role = self._config.actor_role_map.get(actor_id, self._config.actor_role_default)
        channel_type = _channel_type_name(message.channel)
        chat_class = _resolve_chat_class(message.channel)
        project_id = parsed.project_id
        if project_id is None and chat_class == "project":
            project_id = _derive_project_id(message.channel)
        payload, signature = build_discord_ingress_payload(
            parsed_command=parsed,
            message_id=str(message.id),
            actor_external_id=actor_id,
            actor_role=actor_role,
            content=message.content,
            guild_id=guild_id,
            channel_id=channel_id,
            channel_type=channel_type,
            chat_class=chat_class,
            connector_shared_secret=self._config.connector_shared_secret,
            project_id=project_id,
            timestamp=message.created_at,
        )
        try:
            response = await self._http_client.post(
                self._ingress_url,
                headers={"X-OpenQilin-Signature": signature},
                json=payload,
            )
        except httpx.HTTPError as error:
            LOGGER.warning(
                "discord.worker.connector_error",
                message_id=str(message.id),
                error=str(error),
            )
            await message.channel.send(
                "[error] code=connector_http_error message=failed to reach OpenQilin control plane"
            )
            return
        try:
            body = response.json()
        except ValueError:
            body = {
                "status": "error",
                "trace_id": payload["trace_id"],
                "error": {
                    "code": "connector_response_invalid_json",
                    "message": "control plane returned invalid JSON",
                },
            }
        response_text = format_governed_response(status_code=response.status_code, body=body)
        await message.channel.send(response_text)


def build_worker_config(settings: RuntimeSettings) -> DiscordBotWorkerConfig:
    """Resolve Discord worker runtime config from settings and env fallbacks."""

    token = settings.discord_bot_token or os.getenv("DISCORD_BOT_TOKEN")
    if token is None or not token.strip():
        raise RuntimeError("discord bot token is required for discord_bot_worker")
    return DiscordBotWorkerConfig(
        token=token.strip(),
        control_plane_base_url=settings.discord_control_plane_base_url,
        connector_shared_secret=settings.connector_shared_secret,
        command_prefix=settings.discord_command_prefix,
        actor_role_default=settings.discord_actor_role_default,
        actor_role_map=parse_actor_role_map(settings.discord_actor_role_map_json),
        allowed_guild_ids=_parse_id_allowlist(settings.discord_allowed_guild_ids_csv),
        allowed_channel_ids=_parse_id_allowlist(settings.discord_allowed_channel_ids_csv),
        request_timeout_seconds=settings.discord_request_timeout_seconds,
    )


async def main(*, run_once: bool = False) -> None:
    """Run Discord bot worker bootstrap and gateway loop."""

    settings = RuntimeSettings()
    enforce_connector_secret_hardening(settings)
    LOGGER.info("worker.bootstrap", worker="discord_bot_worker")
    if run_once:
        _mark_ready()
        return
    config = build_worker_config(settings)
    client = OpenQilinDiscordClient(config=config)
    await client.start(config.token)


if __name__ == "__main__":
    asyncio.run(main())
