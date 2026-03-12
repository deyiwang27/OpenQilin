"""In-memory alert emitter with release-readiness routing semantics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from openqilin.observability.alerts.release_readiness import (
    ReleaseAlertDefinition,
    release_alert_definitions_by_type,
)
from openqilin.observability.audit.audit_writer import InMemoryAuditWriter
from openqilin.observability.metrics.recorder import InMemoryMetricRecorder
from openqilin.observability.tracing.spans import utc_now

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
    """Emit release alerts and record alert observability evidence."""

    def __init__(
        self,
        *,
        metric_recorder: InMemoryMetricRecorder | None = None,
        audit_writer: InMemoryAuditWriter | None = None,
        definitions: dict[str, ReleaseAlertDefinition] | None = None,
    ) -> None:
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
        source_owner_role = (
            "unknown" if owner_resolution_fallback else definition.route.source_owner_role
        )
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
