"""Discord channel lifecycle automator for project spaces."""

from __future__ import annotations

import httpx
import structlog

LOGGER = structlog.get_logger(__name__)

_DISCORD_API_BASE = "https://discord.com/api/v10"
_CHANNEL_TYPE_TEXT = 0


class DiscordChannelAutomator:
    """Creates, archives and locks Discord channels for project spaces.

    Uses the Discord REST API directly with the configured bot token.
    Requires the bot to have the "Manage Channels" permission in the guild.
    """

    def __init__(self, *, bot_token: str) -> None:
        self._bot_token = bot_token

    def create_channel(self, project_id: str, guild_id: str, *, channel_name: str) -> str:
        """Create a Discord text channel for a project space.

        Returns the Discord channel_id (snowflake string) on success.
        Raises DiscordChannelError on API failure.
        """

        url = f"{_DISCORD_API_BASE}/guilds/{guild_id}/channels"
        headers = {
            "Authorization": f"Bot {self._bot_token}",
            "Content-Type": "application/json",
        }
        body = {"name": channel_name, "type": _CHANNEL_TYPE_TEXT}

        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=body)

        if response.status_code not in (200, 201):
            LOGGER.error(
                "discord_automator.create_channel.failed",
                project_id=project_id,
                guild_id=guild_id,
                channel_name=channel_name,
                status_code=response.status_code,
                response_body=response.text[:500],
            )
            raise DiscordChannelError(
                f"Discord API returned {response.status_code} creating channel "
                f"'{channel_name}' in guild {guild_id}"
            )

        channel_id: str = response.json()["id"]
        LOGGER.info(
            "discord_automator.create_channel.ok",
            project_id=project_id,
            guild_id=guild_id,
            channel_id=channel_id,
            channel_name=channel_name,
        )
        return channel_id

    def archive_channel(self, channel_id: str) -> None:
        """Archive a Discord channel (stub — real implementation deferred)."""
        LOGGER.info("discord_automator.archive_channel", channel_id=channel_id, stub=True)

    def lock_channel(self, channel_id: str) -> None:
        """Lock a Discord channel (stub — real implementation deferred)."""
        LOGGER.info("discord_automator.lock_channel", channel_id=channel_id, stub=True)


class DiscordChannelError(Exception):
    """Raised when the Discord channel API call fails."""
