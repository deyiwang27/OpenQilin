from openqilin.observability.testing.stubs import InMemoryAuditWriter
from openqilin.observability.testing.stubs import InMemoryMetricRecorder
from openqilin.observability.tracing.spans import OWNER_COMMAND_INGRESS_SPAN
from openqilin.observability.testing.stubs import InMemoryTracer


def test_in_memory_tracer_records_completed_span() -> None:
    tracer = InMemoryTracer()

    with tracer.start_span(
        trace_id="trace-wp6-unit-1",
        name=OWNER_COMMAND_INGRESS_SPAN,
        attributes={"component": "control_plane"},
    ) as span:
        span.set_attribute("outcome", "accepted")

    spans = tracer.get_spans()
    assert len(spans) == 1
    assert spans[0].trace_id == "trace-wp6-unit-1"
    assert spans[0].name == OWNER_COMMAND_INGRESS_SPAN
    assert spans[0].status == "ok"
    assert ("outcome", "accepted") in spans[0].attributes


def test_in_memory_audit_writer_appends_event_with_correlation_fields() -> None:
    writer = InMemoryAuditWriter()

    event = writer.write_event(
        event_type="owner_command.accepted",
        outcome="accepted",
        trace_id="trace-wp6-unit-2",
        request_id="req-wp6-unit-2",
        task_id="task-wp6-unit-2",
        principal_id="owner_wp6_unit_2",
        source="dispatch_sandbox",
        reason_code=None,
        message="sandbox dispatch accepted",
        attributes={"dispatch_id": "dispatch-wp6-unit-2"},
    )

    events = writer.get_events()
    assert len(events) == 1
    assert events[0] == event
    assert event.trace_id == "trace-wp6-unit-2"
    assert event.request_id == "req-wp6-unit-2"
    assert event.task_id == "task-wp6-unit-2"
    assert event.actor_id == "owner_wp6_unit_2"
    assert event.actor_role == "unknown-role"
    assert event.policy_version == "policy-version-unknown"
    assert event.policy_hash == "policy-hash-unknown"
    assert ("dispatch_id", "dispatch-wp6-unit-2") in event.attributes


def test_in_memory_metric_recorder_tracks_labeled_counters() -> None:
    recorder = InMemoryMetricRecorder()

    recorder.increment_counter(
        "owner_command_admission_outcomes_total",
        labels={"outcome": "blocked", "source": "policy_runtime"},
    )
    recorder.increment_counter(
        "owner_command_admission_outcomes_total",
        labels={"outcome": "blocked", "source": "policy_runtime"},
    )

    value = recorder.get_counter_value(
        "owner_command_admission_outcomes_total",
        labels={"outcome": "blocked", "source": "policy_runtime"},
    )

    assert value == 2
