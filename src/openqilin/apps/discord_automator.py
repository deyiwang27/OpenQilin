"""Discord automation utilities for startup tasks.

M15-WP6: announce_grafana_dashboard_url() sends the Grafana dashboard URL
to the #leadership_council channel on bot startup (best-effort).
"""

from __future__ import annotations

from typing import Any, Protocol, cast

import structlog

LOGGER = structlog.get_logger(__name__)

_LEADERSHIP_COUNCIL_CHANNEL_NAME = "leadership_council"


class _DiscordTextChannel(Protocol):
    async def send(self, message: str) -> Any: ...


async def announce_grafana_dashboard_url(client: object, grafana_public_url: str) -> None:
    """Send the Grafana dashboard URL to #leadership_council on startup.

    Best-effort: logs a warning and returns if the channel is not found or
    the send fails. Never raises - a failed announcement must not block startup.

    Args:
        client: A connected discord.Client instance (typed as object to avoid
                importing discord at module level in tests).
        grafana_public_url: The public Grafana URL to announce. If empty,
                            returns immediately without scanning guilds.
    """
    if not grafana_public_url:
        return

    target_channel = _find_leadership_council_channel(client)
    if target_channel is None:
        LOGGER.warning(
            "discord_automator.channel_not_found",
            channel=_LEADERSHIP_COUNCIL_CHANNEL_NAME,
            grafana_public_url=grafana_public_url,
        )
        return

    try:
        channel = cast(_DiscordTextChannel, target_channel)
        await channel.send(f"\U0001f517 Grafana Operator Dashboard: {grafana_public_url}")
        LOGGER.info(
            "discord_automator.dashboard_url_announced",
            channel=_LEADERSHIP_COUNCIL_CHANNEL_NAME,
            grafana_public_url=grafana_public_url,
        )
    except Exception as error:
        LOGGER.warning(
            "discord_automator.announce_failed",
            channel=_LEADERSHIP_COUNCIL_CHANNEL_NAME,
            grafana_public_url=grafana_public_url,
            error=str(error),
        )


def _find_leadership_council_channel(client: object) -> object | None:
    """Return the first #leadership_council text channel found across all guilds.

    Returns None if no such channel exists or client has no guilds.
    """
    guilds = getattr(client, "guilds", [])
    for guild in guilds:
        channels = getattr(guild, "text_channels", [])
        for channel in channels:
            name = getattr(channel, "name", "")
            if str(name).strip().lower().replace("-", "_") == _LEADERSHIP_COUNCIL_CHANNEL_NAME:
                return channel
    return None
