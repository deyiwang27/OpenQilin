"""Sandbox callback event scaffolding aligned with orchestrator callback contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SandboxOutcome = Literal["completed", "failed"]


@dataclass(frozen=True, slots=True)
class SandboxCallbackEvent:
    """Normalized sandbox callback event."""

    callback_id: str
    task_id: str
    trace_id: str
    outcome: SandboxOutcome
    message: str
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class SandboxCallbackResult:
    """Sandbox callback processing result."""

    applied: bool
    replayed: bool
    message: str


class InMemorySandboxEventCallbackProcessor:
    """Duplicate-safe sandbox callback processor scaffold."""

    def __init__(self) -> None:
        self._processed_callback_ids: set[str] = set()

    def process(self, event: SandboxCallbackEvent) -> SandboxCallbackResult:
        """Process sandbox callback event with duplicate-safe semantics."""

        if event.callback_id in self._processed_callback_ids:
            return SandboxCallbackResult(
                applied=False,
                replayed=True,
                message="sandbox callback already processed",
            )
        self._processed_callback_ids.add(event.callback_id)
        return SandboxCallbackResult(
            applied=True,
            replayed=False,
            message=event.message,
        )
