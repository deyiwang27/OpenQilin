"""Shared DTO placeholders."""

from dataclasses import dataclass


@dataclass(slots=True)
class Envelope:
    """Minimal placeholder envelope used by module scaffolds."""

    trace_id: str
