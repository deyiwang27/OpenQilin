"""In-memory metrics recorder and OTel metrics configuration for observability wiring."""

from __future__ import annotations

import logging
from dataclasses import dataclass


_logger = logging.getLogger(__name__)


def configure_metrics(otlp_endpoint: str) -> None:
    """Configure the global OTel MeterProvider with OTLP gRPC export.

    Call once at application startup when ``OPENQILIN_OTLP_ENDPOINT`` is set.
    """

    from opentelemetry import metrics
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
    reader = PeriodicExportingMetricReader(exporter)
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    _logger.info("OTel metrics configured with OTLP endpoint: %s", otlp_endpoint)


@dataclass(frozen=True, slots=True)
class CounterRecord:
    """Immutable snapshot of a labeled counter."""

    name: str
    labels: tuple[tuple[str, str], ...]
    value: int
