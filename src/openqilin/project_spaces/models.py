"""Domain models for project space binding and routing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class BindingState(str, Enum):
    """Lifecycle states for a project space binding.

    Transition path: proposed → pending_approval → active → archived → locked
    """

    PROPOSED = "proposed"
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    ARCHIVED = "archived"
    LOCKED = "locked"


@dataclass
class ProjectSpaceBinding:
    """Persistent record mapping a Discord channel to a project space."""

    id: str
    project_id: str
    guild_id: str
    channel_id: str
    binding_state: BindingState
    default_recipient: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class RoutingContext:
    """Resolved routing context for an inbound Discord message.

    Returned by ProjectSpaceRoutingResolver.resolve().
    None returned instead when channel is unknown (fail-closed).
    """

    project_id: str
    default_recipient: str
    binding_state: BindingState


@dataclass(frozen=True)
class LifecycleEvent:
    """Event that triggers a binding state transition."""

    event_type: str  # "activate" | "archive" | "lock"
