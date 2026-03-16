"""In-memory tracer and OTel tracer/log configuration for observability wiring."""

from __future__ import annotations

import logging
from typing import Literal, Mapping, Self
from uuid import uuid4

from openqilin.observability.tracing.spans import SpanRecord, normalize_attributes, utc_now

_logger = logging.getLogger(__name__)


def configure_tracer(otlp_endpoint: str) -> None:
    """Configure the global OTel TracerProvider with OTLP gRPC export.

    Idempotent: safe to call multiple times (subsequent calls replace the provider).
    Call once at application startup when ``OPENQILIN_OTLP_ENDPOINT`` is set.
    """

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _logger.info("OTel tracer configured with OTLP endpoint: %s", otlp_endpoint)


def configure_otel_logs(otlp_endpoint: str) -> None:
    """Configure the global OTel LoggerProvider with OTLP gRPC export.

    Used by OTelAuditWriter for streaming audit log records.
    """

    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    exporter = OTLPLogExporter(endpoint=otlp_endpoint, insecure=True)
    provider = LoggerProvider()
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    set_logger_provider(provider)
    _logger.info("OTel log provider configured with OTLP endpoint: %s", otlp_endpoint)


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
