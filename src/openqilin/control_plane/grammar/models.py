"""Grammar layer data models: IntentClass, CommandEnvelope, RoutingHint, ChatContext."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IntentClass(str, Enum):
    """Classification of owner message intent before routing."""

    DISCUSSION = "discussion"
    QUERY = "query"
    MUTATION = "mutation"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class ChatContext:
    """Routing context derived from Discord channel and project binding."""

    chat_class: str
    channel_id: str
    project_id: str | None = None


@dataclass(frozen=True, slots=True)
class CommandEnvelope:
    """Parsed compact command: /oq <verb> [target] [args]."""

    verb: str
    target: str | None
    args: list[str]
    raw_input: str


@dataclass(frozen=True, slots=True)
class RoutingHint:
    """Resolved routing target for a classified free-text message."""

    target_role: str
    project_id: str | None
    confidence: float


class GrammarParseError(Exception):
    """Raised when grammar layer cannot parse or classify a message."""

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details: dict = details or {}
