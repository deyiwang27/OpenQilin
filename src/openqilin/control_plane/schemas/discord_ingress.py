"""Discord ingress adapter schemas for connector-to-owner-command mapping."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from openqilin.control_plane.schemas.owner_commands import OwnerCommandRecipient


class DiscordIngressRequest(BaseModel):
    """Discord-native ingress payload mapped into canonical owner-command envelope."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1, max_length=128)
    external_message_id: str = Field(min_length=1, max_length=256)
    actor_external_id: str = Field(min_length=1, max_length=256)
    actor_role: str = Field(min_length=1, max_length=64)
    idempotency_key: str = Field(min_length=8, max_length=128)
    raw_payload_hash: str = Field(min_length=64, max_length=128)
    timestamp: datetime
    content: str = Field(min_length=1, max_length=4000)
    action: str = Field(min_length=1, max_length=128)
    target: str | None = Field(default=None, min_length=1, max_length=128)
    args: list[str] = Field(default_factory=list, max_length=32)
    recipients: list[OwnerCommandRecipient] = Field(min_length=1, max_length=32)
    project_id: str | None = Field(default=None, min_length=1, max_length=128)
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    guild_id: str = Field(min_length=1, max_length=128)
    channel_id: str = Field(min_length=1, max_length=128)
    channel_type: Literal["dm", "group", "text", "thread"]
    chat_class: Literal["direct", "leadership_council", "governance", "executive", "project"]
    bot_role: str | None = Field(default=None, min_length=1, max_length=64)
    bot_id: str | None = Field(default=None, min_length=1, max_length=128)
    bot_user_id: str | None = Field(default=None, min_length=1, max_length=128)
