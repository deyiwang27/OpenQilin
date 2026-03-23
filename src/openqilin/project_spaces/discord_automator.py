"""Discord channel lifecycle automator for project spaces."""

from __future__ import annotations

import httpx
import structlog

LOGGER = structlog.get_logger(__name__)

_DISCORD_API_BASE = "https://discord.com/api/v10"
_CHANNEL_TYPE_TEXT = 0


def _slugify(name: str) -> str:
    """Convert a name to a Discord-safe slug (lowercase, hyphens, no edge hyphens)."""
    import re

    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:90]


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

    def archive_channel(self, channel_id: str, project_name: str) -> None:
        """Rename the Discord channel to 'done-{slug}' when a project completes."""
        new_name = f"done-{_slugify(project_name)}"
        url = f"{_DISCORD_API_BASE}/channels/{channel_id}"
        headers = {
            "Authorization": f"Bot {self._bot_token}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.patch(url, headers=headers, json={"name": new_name})
        if response.status_code not in (200, 201):
            LOGGER.error(
                "discord_automator.archive_channel.failed",
                channel_id=channel_id,
                new_name=new_name,
                status_code=response.status_code,
            )
            raise DiscordChannelError(
                f"Discord API returned {response.status_code} renaming channel {channel_id}"
            )
        LOGGER.info(
            "discord_automator.archive_channel.ok",
            channel_id=channel_id,
            new_name=new_name,
        )

    def lock_channel(self, channel_id: str, project_name: str, guild_id: str) -> None:
        """Rename channel to 'closed-{slug}' and set read-only when a project terminates."""
        new_name = f"closed-{_slugify(project_name)}"
        headers = {
            "Authorization": f"Bot {self._bot_token}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=10.0) as client:
            rename_resp = client.patch(
                f"{_DISCORD_API_BASE}/channels/{channel_id}",
                headers=headers,
                json={"name": new_name},
            )
            if rename_resp.status_code not in (200, 201):
                LOGGER.error(
                    "discord_automator.lock_channel.rename_failed",
                    channel_id=channel_id,
                    status_code=rename_resp.status_code,
                )
                raise DiscordChannelError(
                    f"Discord API returned {rename_resp.status_code} renaming channel {channel_id}"
                )
            perm_resp = client.put(
                f"{_DISCORD_API_BASE}/channels/{channel_id}/permissions/{guild_id}",
                headers=headers,
                json={"type": 0, "allow": "0", "deny": "2048"},
            )
            if perm_resp.status_code not in (200, 201, 204):
                LOGGER.error(
                    "discord_automator.lock_channel.permissions_failed",
                    channel_id=channel_id,
                    guild_id=guild_id,
                    status_code=perm_resp.status_code,
                )
                raise DiscordChannelError(
                    "Discord API returned "
                    f"{perm_resp.status_code} setting permissions on channel {channel_id}"
                )
        LOGGER.info(
            "discord_automator.lock_channel.ok",
            channel_id=channel_id,
            new_name=new_name,
            guild_id=guild_id,
        )


class DiscordChannelError(Exception):
    """Raised when the Discord channel API call fails."""
