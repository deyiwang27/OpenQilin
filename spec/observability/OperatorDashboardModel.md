# OpenQilin - Operator Dashboard Model

Active as of: v2

## 1. Scope
- Defines the operator visibility surface for MVP-v2.
- Covers data sources, required panels, alert routing, and placement conventions.
- Complements `spec/observability/ObservabilityArchitecture.md` (which defines telemetry collection and export); this spec defines how governed runtime data is surfaced to the operator.

## 2. Two-Surface Operating Model

MVP-v2 adopts a two-surface model with a strict separation of concerns:

| Surface | Role |
|---|---|
| **Discord** | All operator interaction: commands, responses, notifications, alerts |
| **Grafana** | All operator visualization: project state, budget, governance, ops telemetry |

No separate dashboard application, lightweight HTML page, or React console is required in MVP-v2. The Grafana instance is self-hosted as part of the existing Docker Compose topology.

## 3. Data Sources

| Data Source | Provides |
|---|---|
| PostgreSQL (via Grafana data source plugin) | Business data: projects, tasks, milestones, budget events, governance state, audit events, agent registry |
| OpenTelemetry (via Grafana data source) | Ops telemetry: agent liveness, LLM call latency, error rates, orchestration health |

Business panels read from the same PostgreSQL tables used by the runtime as source-of-record. No separate ETL pipeline is required for MVP-v2.

## 4. Required Dashboard Panels

### 4.1 Owner Inbox
Purpose: surface items requiring owner attention without reading Discord history.
- Pending decisions (proposals awaiting owner approval)
- Open escalations requiring owner action
- Governance events unreviewed in the last 24 hours
- Source: PostgreSQL (governance repository, task repository)

### 4.2 Projects Overview
Purpose: portfolio-level project health at a glance.
- All projects with: lifecycle state, blocked flag, owner-waiting flag, last activity timestamp
- Total spend by project (current budget period)
- Source: PostgreSQL (project repository, budget repository)

### 4.3 Project Detail
Purpose: per-project operational status.
- Milestone progress and recent task activity
- Active blockers and pending PM actions
- Per-project cost trend (spend over time, by role)
- Source: PostgreSQL (task repository, milestone repository, budget repository)

### 4.4 Budget and Cost
Purpose: cost visibility and budget risk detection.
- Spend vs. allocation by project (current period)
- Spend by role (roll-up across projects)
- Token usage by model class
- Budget threshold status: soft breach and hard breach indicators
- Source: PostgreSQL (budget repository)

### 4.5 System and Runtime Health
Purpose: runtime operational status.
- Agent liveness by role
- LLM call latency by model class
- Error rate by service
- Orchestration worker status
- Source: OpenTelemetry

### 4.6 Audit and Governance Events
Purpose: recent governance activity.
- Recent policy denials and obligation triggers
- Escalation events
- Constitution version and bundle hash in active use
- Failed or cancelled tasks requiring review
- Source: PostgreSQL (audit event repository)

## 5. Alert Routing Posture
- Grafana evaluates threshold alert rules against PostgreSQL and OTel data sources.
- Threshold breach alerts (budget limits, error rate spikes, agent liveness failures) are routed to Discord via Grafana webhook alerting.
- Alert routing in Discord:
  - Severity-based shared alerts → `leadership_council`
  - Lower-severity alerts → `owner <-> secretary` DM
- The owner MUST NOT need to watch the Grafana dashboard to receive alerts; alerts surface in Discord automatically.
- Alert messages MUST be self-describing: include severity, type, source surface, and affected project or subsystem.

## 6. Placement and Access
- The Grafana dashboard URL is pinned in `leadership_council`.
- The same URL may be reflected in the channel topic or description.
- The dashboard is a read-only operator surface; all governed actions are performed in Discord.

## 7. Rule Set
| Rule ID | Statement | Severity | Enforced By |
|---|---|---|---|
| DASH-001 | Grafana MUST be the single operator dashboard in MVP-v2; no separate dashboard application is required. | high | Ops |
| DASH-002 | Business data panels MUST read from PostgreSQL via the Grafana PostgreSQL data source plugin. | critical | Observability |
| DASH-003 | Ops and infrastructure panels MUST read from the OTel data source. | high | Observability |
| DASH-004 | Threshold breach alerts MUST be routed to Discord via Grafana webhook alerting. | high | Observability |
| DASH-005 | The dashboard URL MUST be pinned in `leadership_council`. | medium | Ops |
| DASH-006 | The dashboard MUST enable the owner to identify blocked projects, pending decisions, budget risk, and system health within 2 minutes. | high | Ops |

## 8. Conformance Tests
- Grafana dashboard loads and displays all 6 panel sections without errors after a clean stack start.
- Owner Inbox panel shows pending decisions and escalations sourced from PostgreSQL.
- Projects Overview panel reflects current project lifecycle states from PostgreSQL.
- Budget panel shows correct spend vs. allocation for at least one project.
- System Health panel displays agent liveness and LLM latency sourced from OTel.
- A simulated budget threshold breach triggers a Grafana alert that appears in Discord `leadership_council`.
- The dashboard URL is pinned and accessible from `leadership_council`.
