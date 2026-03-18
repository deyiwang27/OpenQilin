"""Connector identity/channel mapping repository for Discord ingress governance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

IdentityChannelStatus = Literal["pending", "verified", "revoked"]


@dataclass(frozen=True, slots=True)
class IdentityChannelMappingRecord:
    """Persisted connector actor<->channel mapping state."""

    mapping_id: str
    connector: str
    actor_external_id: str
    guild_id: str
    channel_id: str
    channel_type: str
    status: IdentityChannelStatus
    created_at: datetime
    updated_at: datetime
    principal_role: str = "owner"


class IdentityChannelRepositoryError(ValueError):
    """Raised when identity/channel repository contracts are violated."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
