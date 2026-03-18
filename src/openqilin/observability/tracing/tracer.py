"""In-memory tracer and OTel tracer/log configuration for observability wiring."""

from __future__ import annotations

import logging


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
