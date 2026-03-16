"""In-memory metrics recorder and OTel metrics configuration for observability wiring."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping

from openqilin.observability.tracing.spans import normalize_attributes

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


class InMemoryMetricRecorder:
    """Minimal labeled counter recorder."""

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
