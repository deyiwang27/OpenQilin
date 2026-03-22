"""In-memory metrics recorder and OTel metrics configuration for observability wiring."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


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


class OTelMetricRecorder:
    """Production metric recorder backed by the global OTel MeterProvider.

    Lazy-creates OTel Counters by name on first use. When no MeterProvider is
    configured, OTel SDK returns a NoOpMeter - all calls are silently ignored.
    Thread-safe: OTel SDK counter.add() is thread-safe.
    """

    def __init__(self, meter_name: str = "openqilin") -> None:
        from opentelemetry import metrics as otel_metrics

        self._meter = otel_metrics.get_meter(meter_name)
        self._counters: dict[str, Any] = {}

    def increment_counter(
        self,
        name: str,
        *,
        labels: Mapping[str, object] | None = None,
        amount: int = 1,
    ) -> None:
        """Increment a named OTel counter. Creates the counter on first use."""
        if name not in self._counters:
            self._counters[name] = self._meter.create_counter(name)
        attrs = {k: str(v) for k, v in (labels or {}).items()}
        self._counters[name].add(amount, attrs)

    def get_counter_value(
        self,
        name: str,
        *,
        labels: Mapping[str, object] | None = None,
    ) -> int:
        """Compatibility helper for tests that expect an in-memory metric interface.

        OTel counters are write-only from this process boundary, so this always returns 0.
        """
        del name, labels
        return 0


@dataclass(frozen=True, slots=True)
class CounterRecord:
    """Immutable snapshot of a labeled counter."""

    name: str
    labels: tuple[tuple[str, str], ...]
    value: int
