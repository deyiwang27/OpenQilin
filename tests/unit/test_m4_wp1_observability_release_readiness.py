from openqilin.observability.alerts.alert_emitter import (
    AlertEmissionRequest,
    InMemoryAlertEmitter,
)
from openqilin.observability.alerts.release_readiness import (
    build_release_alert_catalog,
    build_release_dashboard_catalog,
)
from openqilin.observability.audit.audit_writer import InMemoryAuditWriter
from openqilin.observability.metrics.recorder import InMemoryMetricRecorder


def test_release_dashboard_catalog_has_minimum_v1_dashboards() -> None:
    dashboards = build_release_dashboard_catalog()

    assert len(dashboards) == 5
    assert {dashboard.dashboard_id for dashboard in dashboards} == {
        "governance_gate_health",
        "task_orchestration_health",
        "communication_reliability",
        "budget_and_escalation",
        "runtime_platform",
    }
    for dashboard in dashboards:
        assert len(dashboard.panels) >= 2


def test_release_alert_catalog_has_expected_thresholds_and_runbooks() -> None:
    alerts = build_release_alert_catalog()

    assert len(alerts) == 6
    by_type = {alert.alert_type: alert for alert in alerts}
    assert by_type["policy_eval_error_spike"].threshold.value == 0.02
    assert by_type["orchestration_deadlock"].threshold.window_minutes == 10
    assert by_type["acp_dead_letter_spike"].route.primary_escalation_role == "cwo"
    assert by_type["collector_ingest_failure"].runbook_ref.startswith(
        "spec/infrastructure/operations/"
    )


def test_alert_emitter_records_metric_and_audit_for_direct_route() -> None:
    metric_recorder = InMemoryMetricRecorder()
    audit_writer = InMemoryAuditWriter()
    emitter = InMemoryAlertEmitter(metric_recorder=metric_recorder, audit_writer=audit_writer)

    result = emitter.emit(
        AlertEmissionRequest(
            trace_id="trace-m4-wp1-alert-001",
            alert_type="orchestration_deadlock",
            severity="critical",
            source_owner_role="administrator",
            rule_ids=("MET-001", "MET-004"),
            message="orchestrator progress stalled for over ten minutes",
            observed_value=3,
        )
    )

    assert result.owner_resolution_fallback is False
    assert result.event.source_owner_role == "administrator"
    assert result.event.next_owner_role == "cwo"
    assert (
        metric_recorder.get_counter_value(
            "governance_alerts_total",
            labels={
                "alert_type": "orchestration_deadlock",
                "severity": "critical",
                "next_owner_role": "cwo",
            },
        )
        == 1
    )
    events = audit_writer.get_events()
    assert len(events) == 1
    assert events[0].event_type == "observability.alert.emitted"
    assert events[0].outcome == "alert_emitted"
    assert events[0].trace_id == "trace-m4-wp1-alert-001"
    payload = dict(events[0].payload)
    assert payload["alert_type"] == "orchestration_deadlock"
    assert payload["source_owner_role"] == "administrator"
    assert payload["catalog_source_owner_role"] == "project_manager"
    assert payload["next_owner_role"] == "cwo"


def test_alert_emitter_falls_back_to_ceo_for_ambiguous_owner() -> None:
    metric_recorder = InMemoryMetricRecorder()
    audit_writer = InMemoryAuditWriter()
    emitter = InMemoryAlertEmitter(metric_recorder=metric_recorder, audit_writer=audit_writer)

    result = emitter.emit(
        AlertEmissionRequest(
            trace_id="trace-m4-wp1-alert-002",
            alert_type="orchestration_deadlock",
            severity="critical",
            source_owner_role=None,
            rule_ids=("MET-002", "MET-003"),
            message="orchestrator progress stalled for over ten minutes",
        )
    )

    assert result.owner_resolution_fallback is True
    assert result.event.next_owner_role == "ceo"
    assert result.event.source_owner_role == "unknown"
    assert (
        metric_recorder.get_counter_value(
            "governance_alerts_total",
            labels={
                "alert_type": "orchestration_deadlock",
                "severity": "critical",
                "next_owner_role": "ceo",
            },
        )
        == 1
    )
    events = audit_writer.get_events()
    assert len(events) == 2
    assert events[0].event_type == "observability.alert.emitted"
    assert events[1].event_type == "observability.alert.owner_resolution"
