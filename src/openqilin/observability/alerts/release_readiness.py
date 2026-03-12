"""Release-readiness dashboard and alert catalog for M4-WP1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AlertSeverity = Literal["warning", "error", "critical"]
ThresholdComparator = Literal["gt", "gte"]


@dataclass(frozen=True, slots=True)
class DashboardPanelDefinition:
    """One metric panel displayed on a release-readiness dashboard."""

    panel_id: str
    title: str
    metric_name: str
    aggregation: str
    unit: str


@dataclass(frozen=True, slots=True)
class DashboardDefinition:
    """Dashboard contract used for release-readiness monitoring."""

    dashboard_id: str
    title: str
    owner_role: str
    panels: tuple[DashboardPanelDefinition, ...]


@dataclass(frozen=True, slots=True)
class AlertThresholdDefinition:
    """Alert threshold contract for one metric signal."""

    metric_name: str
    comparator: ThresholdComparator
    value: float
    window_minutes: int


@dataclass(frozen=True, slots=True)
class AlertRouteDefinition:
    """Alert ownership routing contract."""

    source_owner_role: str
    primary_escalation_role: str
    fallback_role: str


@dataclass(frozen=True, slots=True)
class ReleaseAlertDefinition:
    """Release alert definition bound to threshold and routing ownership."""

    alert_type: str
    severity: AlertSeverity
    threshold: AlertThresholdDefinition
    route: AlertRouteDefinition
    runbook_ref: str


def build_release_dashboard_catalog() -> tuple[DashboardDefinition, ...]:
    """Build the minimum release-readiness dashboard catalog."""

    return (
        DashboardDefinition(
            dashboard_id="governance_gate_health",
            title="Governance Gate Health",
            owner_role="auditor",
            panels=(
                DashboardPanelDefinition(
                    panel_id="policy_deny_rate",
                    title="Policy Deny Rate",
                    metric_name="owner_command_admission_outcomes_total",
                    aggregation="rate_by_outcome",
                    unit="ratio",
                ),
                DashboardPanelDefinition(
                    panel_id="policy_eval_errors",
                    title="Policy Evaluation Errors",
                    metric_name="owner_command_admission_outcomes_total",
                    aggregation="rate_by_reason_code",
                    unit="ratio",
                ),
            ),
        ),
        DashboardDefinition(
            dashboard_id="task_orchestration_health",
            title="Task Orchestration Health",
            owner_role="cwo",
            panels=(
                DashboardPanelDefinition(
                    panel_id="task_blocked_rate",
                    title="Task Blocked Rate",
                    metric_name="owner_command_admission_outcomes_total",
                    aggregation="rate_by_outcome",
                    unit="ratio",
                ),
                DashboardPanelDefinition(
                    panel_id="dispatch_latency",
                    title="Dispatch Latency",
                    metric_name="owner_command_dispatch_latency_seconds",
                    aggregation="p95",
                    unit="seconds",
                ),
            ),
        ),
        DashboardDefinition(
            dashboard_id="communication_reliability",
            title="Communication Reliability",
            owner_role="administrator",
            panels=(
                DashboardPanelDefinition(
                    panel_id="callback_replay_rate",
                    title="Callback Replay Rate",
                    metric_name="communication_callback_events_total",
                    aggregation="rate_by_replayed",
                    unit="ratio",
                ),
                DashboardPanelDefinition(
                    panel_id="dead_letter_rate",
                    title="Dead-letter Rate",
                    metric_name="communication_dead_letter_total",
                    aggregation="rate",
                    unit="ratio",
                ),
            ),
        ),
        DashboardDefinition(
            dashboard_id="budget_and_escalation",
            title="Budget and Escalation",
            owner_role="auditor",
            panels=(
                DashboardPanelDefinition(
                    panel_id="budget_hard_breach_count",
                    title="Budget Hard Breach Count",
                    metric_name="budget_hard_breach_total",
                    aggregation="sum",
                    unit="count",
                ),
                DashboardPanelDefinition(
                    panel_id="containment_latency",
                    title="Containment Latency",
                    metric_name="governance_containment_latency_seconds",
                    aggregation="p95",
                    unit="seconds",
                ),
            ),
        ),
        DashboardDefinition(
            dashboard_id="runtime_platform",
            title="Runtime Platform",
            owner_role="administrator",
            panels=(
                DashboardPanelDefinition(
                    panel_id="collector_ingest_failures",
                    title="Collector Ingest Failures",
                    metric_name="otel_collector_ingest_failures_total",
                    aggregation="rate",
                    unit="count",
                ),
                DashboardPanelDefinition(
                    panel_id="error_budget_burn",
                    title="Error Budget Burn",
                    metric_name="runtime_error_budget_burn_ratio",
                    aggregation="latest",
                    unit="ratio",
                ),
            ),
        ),
    )


def build_release_alert_catalog() -> tuple[ReleaseAlertDefinition, ...]:
    """Build release alert thresholds and routing ownership matrix."""

    return (
        ReleaseAlertDefinition(
            alert_type="policy_eval_error_spike",
            severity="critical",
            threshold=AlertThresholdDefinition(
                metric_name="owner_command_admission_outcomes_total",
                comparator="gt",
                value=0.02,
                window_minutes=5,
            ),
            route=AlertRouteDefinition(
                source_owner_role="auditor",
                primary_escalation_role="owner",
                fallback_role="ceo",
            ),
            runbook_ref="spec/infrastructure/operations/FailureAndRecoveryModel.md#2-recovery-posture-by-class",
        ),
        ReleaseAlertDefinition(
            alert_type="budget_hard_breach_detected",
            severity="critical",
            threshold=AlertThresholdDefinition(
                metric_name="budget_hard_breach_total",
                comparator="gte",
                value=1.0,
                window_minutes=1,
            ),
            route=AlertRouteDefinition(
                source_owner_role="auditor",
                primary_escalation_role="owner",
                fallback_role="ceo",
            ),
            runbook_ref="spec/governance/architecture/EscalationModel.md#5-v1-operational-escalation-paths",
        ),
        ReleaseAlertDefinition(
            alert_type="safety_critical_incident",
            severity="critical",
            threshold=AlertThresholdDefinition(
                metric_name="safety_critical_incident_total",
                comparator="gte",
                value=1.0,
                window_minutes=1,
            ),
            route=AlertRouteDefinition(
                source_owner_role="auditor",
                primary_escalation_role="owner",
                fallback_role="ceo",
            ),
            runbook_ref="spec/infrastructure/operations/FailureAndRecoveryModel.md#2-recovery-posture-by-class",
        ),
        ReleaseAlertDefinition(
            alert_type="orchestration_deadlock",
            severity="critical",
            threshold=AlertThresholdDefinition(
                metric_name="task_orchestrator_no_progress_minutes",
                comparator="gt",
                value=10.0,
                window_minutes=10,
            ),
            route=AlertRouteDefinition(
                source_owner_role="project_manager",
                primary_escalation_role="cwo",
                fallback_role="ceo",
            ),
            runbook_ref="spec/infrastructure/operations/FailureAndRecoveryModel.md#3-restart-policy-boundaries",
        ),
        ReleaseAlertDefinition(
            alert_type="acp_dead_letter_spike",
            severity="critical",
            threshold=AlertThresholdDefinition(
                metric_name="communication_dead_letter_total",
                comparator="gt",
                value=0.01,
                window_minutes=10,
            ),
            route=AlertRouteDefinition(
                source_owner_role="administrator",
                primary_escalation_role="cwo",
                fallback_role="ceo",
            ),
            runbook_ref="spec/infrastructure/operations/FailureAndRecoveryModel.md#2-recovery-posture-by-class",
        ),
        ReleaseAlertDefinition(
            alert_type="collector_ingest_failure",
            severity="critical",
            threshold=AlertThresholdDefinition(
                metric_name="otel_collector_ingest_failures_total",
                comparator="gt",
                value=0.0,
                window_minutes=5,
            ),
            route=AlertRouteDefinition(
                source_owner_role="administrator",
                primary_escalation_role="owner",
                fallback_role="ceo",
            ),
            runbook_ref="spec/infrastructure/operations/DeploymentTopologyAndOps.md#5-deployment-pattern-phasing",
        ),
    )


def release_alert_definitions_by_type() -> dict[str, ReleaseAlertDefinition]:
    """Index release alert definitions by alert type."""

    return {definition.alert_type: definition for definition in build_release_alert_catalog()}
