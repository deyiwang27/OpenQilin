"""Observability test stubs — canonical home for InMemory* introspection helpers.

These stubs are for unit/component tests only.  They MUST NOT be imported by
production code paths.  The CI grep gate enforces this:

    grep -r --include="*.py" -l "class InMemory" src/ \\
        | grep -v "/testing/" | grep -v "tests/"
    # Must return zero results.

Import these from this module:

    from openqilin.observability.testing.stubs import (
        InMemoryAuditWriter,
        InMemorySpan,
        InMemoryTracer,
        InMemoryMetricRecorder,
        InMemoryAlertEmitter,
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, Literal, Mapping, Self
from uuid import uuid4

from openqilin.observability.audit.audit_writer import AuditEvent as AuditEvent
from openqilin.observability.tracing.spans import SpanRecord, normalize_attributes, utc_now

if TYPE_CHECKING:
    from openqilin.observability.alerts.release_readiness import ReleaseAlertDefinition

_logger = logging.getLogger(__name__)


class InMemoryAuditWriter:
    """Stores audit events in memory for deterministic tests."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def write_event(
        self,
        *,
        event_type: str,
        outcome: str,
        trace_id: str,
        request_id: str | None,
        task_id: str | None,
        principal_id: str | None,
        principal_role: str | None = None,
        source: str,
        reason_code: str | None,
        message: str,
        policy_version: str | None = None,
        policy_hash: str | None = None,
        rule_ids: Iterable[str] | None = None,
        payload: dict[str, object] | None = None,
        attributes: dict[str, object] | None = None,
    ) -> AuditEvent:
        """Append a normalized audit event and return it."""

        timestamp = utc_now()
        normalized_rule_ids = tuple(sorted(str(rule_id) for rule_id in (rule_ids or ())))
        normalized_payload = normalize_attributes(
            payload
            or {
                "outcome": outcome,
                "source": source,
                "message": message,
                "request_id": request_id,
                "task_id": task_id,
                "reason_code": reason_code,
            }
        )
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            timestamp=timestamp,
            outcome=outcome,
            trace_id=trace_id,
            actor_id=principal_id or "unknown-actor",
            actor_role=principal_role or "unknown-role",
            policy_version=policy_version or "policy-version-unknown",
            policy_hash=policy_hash or "policy-hash-unknown",
            rule_ids=normalized_rule_ids,
            payload=normalized_payload,
            request_id=request_id,
            task_id=task_id,
            principal_id=principal_id,
            source=source,
            reason_code=reason_code,
            message=message,
            attributes=normalize_attributes(attributes),
            created_at=timestamp,
        )
        self._events.append(event)
        return event

    def get_events(self) -> tuple[AuditEvent, ...]:
        """Return immutable snapshot of audit events."""

        return tuple(self._events)


# ---------------------------------------------------------------------------
# InMemoryMetricRecorder
# ---------------------------------------------------------------------------
from openqilin.observability.metrics.recorder import CounterRecord as CounterRecord  # noqa: E402


class InMemoryMetricRecorder:
    """Minimal labeled counter recorder for tests."""

    def __init__(self) -> None:
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}

    def increment_counter(
        self,
        name: str,
        *,
        labels: Mapping[str, object] | None = None,
        amount: int = 1,
    ) -> None:
        """Increment a named counter with optional labels."""

        normalized_labels = normalize_attributes(labels)
        key = (name, normalized_labels)
        self._counters[key] = self._counters.get(key, 0) + amount

    def get_counter_value(
        self,
        name: str,
        *,
        labels: Mapping[str, object] | None = None,
    ) -> int:
        """Read counter value for a specific label set."""

        key = (name, normalize_attributes(labels))
        return self._counters.get(key, 0)

    def get_counters(self) -> tuple[CounterRecord, ...]:
        """Return immutable snapshot of all recorded counters."""

        return tuple(
            CounterRecord(name=name, labels=labels, value=value)
            for (name, labels), value in sorted(self._counters.items())
        )


# ---------------------------------------------------------------------------
# InMemorySpan / InMemoryTracer
# ---------------------------------------------------------------------------


class InMemorySpan:
    """Mutable span context captured by the in-memory tracer."""

    def __init__(
        self,
        tracer: "InMemoryTracer",
        *,
        trace_id: str,
        name: str,
        attributes: Mapping[str, object] | None = None,
    ) -> None:
        self._tracer = tracer
        self._span_id = str(uuid4())
        self._trace_id = trace_id
        self._name = name
        self._attributes: dict[str, str] = {
            str(key): str(value) for key, value in (attributes or {}).items()
        }
        self._status = "ok"
        self._started_at = utc_now()
        self._ended = False

    @property
    def trace_id(self) -> str:
        """Return span trace identifier."""

        return self._trace_id

    def set_attribute(self, key: str, value: object) -> None:
        """Attach string-normalized attribute to the span."""

        self._attributes[str(key)] = str(value)

    def set_status(self, status: str) -> None:
        """Override span terminal status."""

        self._status = status

    def end(self) -> None:
        """Finalize span and append immutable record to tracer."""

        if self._ended:
            return
        self._ended = True
        self._tracer.record(
            SpanRecord(
                span_id=self._span_id,
                trace_id=self._trace_id,
                name=self._name,
                status=self._status,
                started_at=self._started_at,
                ended_at=utc_now(),
                attributes=normalize_attributes(self._attributes),
            )
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> Literal[False]:
        if exc is not None:
            self._status = "error"
        self.end()
        return False


class InMemoryTracer:
    """Simple append-only tracer for tests and local evidence."""

    def __init__(self) -> None:
        self._spans: list[SpanRecord] = []

    def start_span(
        self,
        *,
        trace_id: str,
        name: str,
        attributes: Mapping[str, object] | None = None,
    ) -> InMemorySpan:
        """Create a mutable in-memory span context."""

        return InMemorySpan(
            tracer=self,
            trace_id=trace_id,
            name=name,
            attributes=attributes,
        )

    def record(self, span: SpanRecord) -> None:
        """Record a completed span."""

        self._spans.append(span)

    def get_spans(self) -> tuple[SpanRecord, ...]:
        """Return immutable snapshot of recorded spans."""

        return tuple(self._spans)


# ---------------------------------------------------------------------------
# InMemoryAlertEmitter
# ---------------------------------------------------------------------------
AlertSeverity = Literal["warning", "error", "critical"]


@dataclass(frozen=True, slots=True)
class AlertEmissionRequest:
    """Alert emission request payload."""

    trace_id: str
    alert_type: str
    severity: AlertSeverity
    source_owner_role: str | None
    rule_ids: tuple[str, ...]
    message: str
    observed_value: float | None = None


@dataclass(frozen=True, slots=True)
class AlertEvent:
    """Alert event payload with required release-readiness metadata."""

    event_id: str
    trace_id: str
    alert_type: str
    severity: AlertSeverity
    source_owner_role: str
    next_owner_role: str
    rule_ids: tuple[str, ...]
    timestamp: str
    message: str
    runbook_ref: str


@dataclass(frozen=True, slots=True)
class AlertEmissionResult:
    """Alert emission result including ownership-resolution behavior."""

    event: AlertEvent
    owner_resolution_fallback: bool


class InMemoryAlertEmitter:
    """Emit release alerts and record alert observability evidence (test stub)."""

    def __init__(
        self,
        *,
        metric_recorder: InMemoryMetricRecorder | None = None,
        audit_writer: InMemoryAuditWriter | None = None,
        definitions: dict[str, ReleaseAlertDefinition] | None = None,
    ) -> None:
        from openqilin.observability.alerts.release_readiness import (
            release_alert_definitions_by_type,
        )

        self._metric_recorder = metric_recorder or InMemoryMetricRecorder()
        self._audit_writer = audit_writer or InMemoryAuditWriter()
        self._definitions = definitions or release_alert_definitions_by_type()
        self._events: list[AlertEvent] = []

    def emit(self, request: AlertEmissionRequest) -> AlertEmissionResult:
        """Emit one alert event with deterministic routing fallback behavior."""

        definition = self._definitions.get(request.alert_type)
        if definition is None:
            raise ValueError(f"unsupported release alert type: {request.alert_type}")

        normalized_source_owner = (request.source_owner_role or "").strip()
        owner_resolution_fallback = normalized_source_owner in {"", "unknown", "ambiguous"}
        next_owner_role = (
            "ceo" if owner_resolution_fallback else definition.route.primary_escalation_role
        )
        source_owner_role = "unknown" if owner_resolution_fallback else normalized_source_owner
        event = AlertEvent(
            event_id=str(uuid4()),
            trace_id=request.trace_id,
            alert_type=request.alert_type,
            severity=request.severity,
            source_owner_role=source_owner_role,
            next_owner_role=next_owner_role,
            rule_ids=tuple(sorted(request.rule_ids)),
            timestamp=utc_now().isoformat(),
            message=request.message,
            runbook_ref=definition.runbook_ref,
        )
        self._events.append(event)
        self._metric_recorder.increment_counter(
            "governance_alerts_total",
            labels={
                "alert_type": event.alert_type,
                "severity": event.severity,
                "next_owner_role": event.next_owner_role,
            },
        )
        self._audit_writer.write_event(
            event_type="observability.alert.emitted",
            outcome="alert_emitted",
            trace_id=event.trace_id,
            request_id=None,
            task_id=None,
            principal_id=f"role:{source_owner_role}",
            principal_role=source_owner_role,
            source="observability_alert_emitter",
            reason_code=event.alert_type,
            message=event.message,
            rule_ids=event.rule_ids,
            payload={
                "event_id": event.event_id,
                "alert_type": event.alert_type,
                "severity": event.severity,
                "source_owner_role": event.source_owner_role,
                "catalog_source_owner_role": definition.route.source_owner_role,
                "next_owner_role": event.next_owner_role,
                "timestamp": event.timestamp,
                "runbook_ref": event.runbook_ref,
                "observed_value": request.observed_value
                if request.observed_value is not None
                else "",
            },
        )
        if owner_resolution_fallback:
            self._audit_writer.write_event(
                event_type="observability.alert.owner_resolution",
                outcome="owner_resolution_fallback",
                trace_id=event.trace_id,
                request_id=None,
                task_id=None,
                principal_id="role:ceo",
                principal_role="ceo",
                source="observability_alert_emitter",
                reason_code="alert_owner_ambiguous",
                message="alert source owner unresolved; fallback route to ceo",
                rule_ids=event.rule_ids,
                payload={
                    "event_id": event.event_id,
                    "alert_type": event.alert_type,
                    "resolved_owner_role": "ceo",
                },
            )
        return AlertEmissionResult(
            event=event,
            owner_resolution_fallback=owner_resolution_fallback,
        )

    def get_events(self) -> tuple[AlertEvent, ...]:
        """Return immutable snapshot of emitted alert events."""

        return tuple(self._events)


__all__ = [
    "AlertEmissionRequest",
    "AlertEmissionResult",
    "AlertEvent",
    "AlertSeverity",
    "AuditEvent",
    "CounterRecord",
    "InMemoryAlertEmitter",
    "InMemoryAuditWriter",
    "InMemoryMetricRecorder",
    "InMemorySpan",
    "InMemoryTracer",
]
