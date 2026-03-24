"""Shared request/response models for conversational free-text advisory."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FreeTextAdvisoryRequest:
    """Carries a free-text @mention message to an agent advisory handler."""

    text: str
    scope: str
    guild_id: str
    channel_id: str
    addressed_agent: str | None = None


@dataclass(frozen=True, slots=True)
class FreeTextAdvisoryResponse:
    """Wraps advisory text returned from a free-text agent interaction."""

    advisory_text: str
