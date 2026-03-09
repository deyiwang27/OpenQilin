# OpenQilin - Observability Architecture Specification

## 1. Scope
- Defines required telemetry for governance, runtime, and auditability.
- This document is a component-spec under `spec/infrastructure/RuntimeArchitecture.md`.
- It MUST inherit global runtime contracts `RT-001..RT-006`.

Observability stack posture (v1):
- baseline: OpenTelemetry + Grafana.
- system overlays: LangSmith + AgentOps.

## 2. Event Schema (Required Fields)
```json
{
  "event_id": "uuid",
  "event_type": "string",
  "timestamp": "RFC3339",
  "trace_id": "uuid",
  "actor_id": "string",
  "actor_role": "string",
  "rule_ids": ["string"],
  "severity": "info|warning|error|critical",
  "payload": {}
}
```

## 3. Telemetry Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| OBS-001 | All policy decisions MUST emit telemetry events. | critical | observability |
| OBS-002 | All lifecycle transitions MUST emit telemetry events. | high | runtime |
| OBS-003 | All budget threshold crossings MUST emit telemetry events. | critical | budget_engine |
| OBS-004 | Critical incidents MUST page governance channels. | critical | observability |

## 4. Metrics Baseline
- Authorization deny rate
- Budget breach count
- Task failure rate by role
- Mean time to containment

## 5. Tooling Layers
- OpenTelemetry: canonical telemetry substrate.
- Grafana: dashboards, alert routing, and operations views.
- LangSmith: LLM trace and evaluation workflows.
- AgentOps: cost and operational analytics overlays.

## 6. Conformance Tests
- Missing `trace_id` events are rejected.
- Critical incident always generates alert.
- Policy decision, task dispatch, and sandbox execution events share the same `trace_id`.
- Budget hard-threshold events include telemetry payload with policy metadata.
- Overlay telemetry from LangSmith/AgentOps remains trace-correlated to baseline telemetry.
