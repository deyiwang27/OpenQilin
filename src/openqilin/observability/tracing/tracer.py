"""In-memory tracer used by M1 observability wiring."""

from __future__ import annotations

from typing import Literal, Mapping, Self
from uuid import uuid4

from openqilin.observability.tracing.spans import SpanRecord, normalize_attributes, utc_now


class InMemorySpan:
    """Mutable span context captured by the in-memory tracer."""

    def __init__(
        self,
        tracer: InMemoryTracer,
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
