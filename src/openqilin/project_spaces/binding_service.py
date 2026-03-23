"""Project space binding service — orchestrates channel creation and state transitions."""

from __future__ import annotations

import logging
import re

from openqilin.project_spaces.binding_repository import (
    PostgresProjectSpaceBindingRepository,
    build_project_space_binding,
)
from openqilin.project_spaces.discord_automator import DiscordChannelAutomator
from openqilin.project_spaces.models import BindingState, LifecycleEvent, ProjectSpaceBinding

LOGGER = logging.getLogger(__name__)

# Legal state transitions driven by LifecycleEvent.event_type.
_TRANSITIONS: dict[str, dict[BindingState, BindingState]] = {
    "approve": {
        BindingState.PROPOSED: BindingState.PENDING_APPROVAL,
    },
    "activate": {
        BindingState.PENDING_APPROVAL: BindingState.ACTIVE,
        BindingState.PROPOSED: BindingState.ACTIVE,  # direct activation allowed
    },
    "archive": {
        BindingState.ACTIVE: BindingState.ARCHIVED,
    },
    "lock": {
        BindingState.ACTIVE: BindingState.LOCKED,
        BindingState.ARCHIVED: BindingState.LOCKED,
    },
}


def _slugify_channel_name(name: str) -> str:
    """Convert a project name to a Discord-safe channel name.

    Discord channel names: lowercase, hyphens, max 100 chars.
    """

    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return f"project-{slug}"[:100]


class ProjectSpaceBindingService:
    """Orchestrates project space binding creation and lifecycle transitions."""

    def __init__(
        self,
        *,
        binding_repo: PostgresProjectSpaceBindingRepository,
        automator: DiscordChannelAutomator,
    ) -> None:
        self._repo = binding_repo
        self._automator = automator

    def create_and_bind(
        self,
        project_id: str,
        guild_id: str,
        project_name: str,
        *,
        default_recipient: str = "project_manager",
    ) -> ProjectSpaceBinding:
        """Create a Discord channel and insert a binding record.

        The binding starts in ACTIVE state (channel is immediately usable).
        """

        channel_id = self._automator.create_channel(
            project_id,
            guild_id,
            channel_name=_slugify_channel_name(project_name),
        )
        binding = build_project_space_binding(
            project_id=project_id,
            guild_id=guild_id,
            channel_id=channel_id,
            default_recipient=default_recipient,
            state=BindingState.ACTIVE,
        )
        stored = self._repo.insert(binding)
        LOGGER.info(
            "project_space.created",
            extra={
                "project_id": project_id,
                "guild_id": guild_id,
                "channel_id": channel_id,
                "binding_id": stored.id,
            },
        )
        return stored

    def transition(
        self,
        project_id: str,
        event: LifecycleEvent,
        project_name: str = "",
    ) -> ProjectSpaceBinding:
        """Apply a lifecycle event to the binding for the given project.

        Raises ValueError if no binding exists or the transition is illegal.
        """

        binding = self._repo.find_by_project_id(project_id)
        if binding is None:
            raise ValueError(f"No binding found for project_id={project_id!r}")

        allowed = _TRANSITIONS.get(event.event_type, {})
        target_state = allowed.get(binding.binding_state)
        if target_state is None:
            raise ValueError(
                f"Illegal transition for project_id={project_id!r}: "
                f"{binding.binding_state.value!r} --[{event.event_type}]--> (no target)"
            )

        updated = self._repo.update_state(binding.id, target_state)

        # Trigger Discord channel operation for relevant transitions.
        if target_state == BindingState.ARCHIVED:
            self._automator.archive_channel(binding.channel_id, project_name)
        elif target_state == BindingState.LOCKED:
            self._automator.lock_channel(binding.channel_id, project_name, binding.guild_id)

        LOGGER.info(
            "project_space.transitioned",
            extra={
                "project_id": project_id,
                "event_type": event.event_type,
                "from_state": binding.binding_state.value,
                "to_state": target_state.value,
            },
        )
        return updated
