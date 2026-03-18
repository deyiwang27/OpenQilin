"""Discord channel lifecycle automator for project spaces.

M13-WP3: Automates Discord channel creation, archiving, and locking in
response to project space binding lifecycle events.

Note: The real Discord Bot API client is out of scope for MVP-v2 (the
Discord connector is inbound-only in M13).  This implementation provides
the correct interface with a local stub that generates deterministic
channel IDs.  A real Discord HTTP client will replace this in a post-MVP
milestone when outbound channel management is activated.
"""

from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)


class DiscordChannelAutomator:
    """Manages Discord channel lifecycle for project spaces.

    Implements:
    - create_channel: provisions a new Discord channel for a project; returns channel_id
    - archive_channel: marks the channel read-only (archived project state)
    - lock_channel: locks the channel for terminal project states
    """

    def create_channel(self, project_id: str, guild_id: str) -> str:
        """Create a Discord channel for the given project in the given guild.

        Returns the new channel_id.

        Note: currently a local stub that returns a deterministic channel_id.
        Real Discord Bot API integration is deferred to post-MVP.
        """

        channel_id = f"ch-{project_id}"
        LOGGER.info(
            "discord_automator.create_channel",
            extra={
                "project_id": project_id,
                "guild_id": guild_id,
                "channel_id": channel_id,
                "stub": True,
            },
        )
        return channel_id

    def archive_channel(self, channel_id: str) -> None:
        """Mark the Discord channel as read-only (archived).

        Corresponds to binding_state transition → archived.
        """

        LOGGER.info(
            "discord_automator.archive_channel",
            extra={"channel_id": channel_id, "stub": True},
        )

    def lock_channel(self, channel_id: str) -> None:
        """Lock the Discord channel for terminal project states.

        Corresponds to binding_state transition → locked.
        """

        LOGGER.info(
            "discord_automator.lock_channel",
            extra={"channel_id": channel_id, "stub": True},
        )
