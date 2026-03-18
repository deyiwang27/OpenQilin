"""Agent registry repository primitives for institutional-agent bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

_INSTITUTIONAL_ROLES = ("administrator", "auditor", "ceo", "cwo", "cso")


@dataclass(frozen=True, slots=True)
class AgentRecord:
    """Persisted agent record under governance registry control."""

    agent_id: str
    role: str
    agent_type: str
    status: str
    created_at: datetime
    updated_at: datetime


class AgentRegistryRepositoryError(ValueError):
    """Raised when agent-registry snapshot persistence cannot be completed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
