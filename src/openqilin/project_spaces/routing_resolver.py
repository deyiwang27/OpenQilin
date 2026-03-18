"""Project space routing resolver — maps Discord channel to project routing context.

PSB-004: default_recipient = project_manager for all project-channel messages.
Unknown or inactive channels return None (fail-closed).
"""

from __future__ import annotations

import logging

from openqilin.project_spaces.binding_repository import PostgresProjectSpaceBindingRepository
from openqilin.project_spaces.models import BindingState, RoutingContext

LOGGER = logging.getLogger(__name__)


class ProjectSpaceRoutingResolver:
    """Resolves a Discord (guild_id, channel_id) pair to a RoutingContext.

    Returns None for:
    - Unknown channels (no binding record)
    - Channels whose binding is not in ACTIVE state

    This is the fail-closed contract: unknown/inactive channels produce no
    routing context, leaving the ingress path to use the payload's project_id
    or reject the message per its own policy.
    """

    def __init__(self, *, binding_repo: PostgresProjectSpaceBindingRepository) -> None:
        self._repo = binding_repo

    def resolve(self, guild_id: str, channel_id: str) -> RoutingContext | None:
        """Resolve a Discord channel to a project routing context.

        Returns RoutingContext if the channel is bound and active.
        Returns None if the channel is unknown or the binding is inactive.
        """

        binding = self._repo.find_by_channel(guild_id, channel_id)
        if binding is None:
            LOGGER.debug(
                "routing_resolver.unknown_channel",
                extra={"guild_id": guild_id, "channel_id": channel_id},
            )
            return None

        if binding.binding_state != BindingState.ACTIVE:
            LOGGER.debug(
                "routing_resolver.inactive_channel",
                extra={
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "binding_state": binding.binding_state.value,
                },
            )
            return None

        return RoutingContext(
            project_id=binding.project_id,
            default_recipient=binding.default_recipient,
            binding_state=binding.binding_state,
        )
