"""Span models and constants for M1 observability tracing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Mapping

OWNER_COMMAND_INGRESS_SPAN = "owner_ingress"
POLICY_EVALUATION_SPAN = "policy_evaluation"
TASK_ORCHESTRATION_SPAN = "task_orchestration"
BUDGET_RESERVATION_SPAN = "budget_reservation"
EXECUTION_SANDBOX_SPAN = "execution_sandbox"
AUDIT_EMIT_SPAN = "audit_emit"


@dataclass(frozen=True, slots=True)
class SpanRecord:
    """Immutable in-memory span record."""

    span_id: str
    trace_id: str
    name: str
    status: str
    started_at: datetime
    ended_at: datetime
    attributes: tuple[tuple[str, str], ...]


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""

    return datetime.now(tz=UTC)


def normalize_attributes(attributes: Mapping[str, object] | None) -> tuple[tuple[str, str], ...]:
    """Normalize span attributes into a stable, immutable tuple."""

    if not attributes:
        return ()
    return tuple(sorted((str(key), str(value)) for key, value in attributes.items()))
