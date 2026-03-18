# ADR-0007 — Grafana Single Provisioned Dashboard Strategy

**Date:** 2026-03-15
**Status:** Approved
**Author:** Claude (Architect)
**Ratified by:** Owner — approved retroactively on 2026-03-17 (M12 merge)
**Supersedes:** —
**Superseded by:** —

---

## Context

OpenQilin's two-surface rule (CLAUDE.md governance constraint): operators interact through **Discord** (actions) and **Grafana** (visibility). No third UI surface is permitted in MVP-v2.

M12-WP5 wired OTel export from all three observability modules. Once real telemetry was flowing, a decision was needed on how to structure the Grafana layer:

1. **How many dashboards?** One shared operator dashboard vs. multiple role-specific views.
2. **How is the dashboard delivered?** Manually created in Grafana UI vs. provisioned from files in version control.
3. **What data sources does Grafana query?** OTel pipeline only vs. direct PostgreSQL queries vs. both.

The operator for MVP-v2 is a single solopreneur. Role-specific dashboards add complexity with no benefit for a one-person operation.

---

## Decision

**One provisioned operator dashboard** (`ops/grafana/dashboards/operator-main.json`), loaded at Grafana startup via Grafana's provisioning mechanism. The dashboard is not editable in the Grafana UI — changes go through version control.

**Three data sources, all provisioned:**
| Source | Purpose |
|---|---|
| `PostgreSQL` | Business panels: task status, audit log, budget usage, agent activity |
| `Prometheus` | Infrastructure metrics: CPU, memory, request rate, error rate |
| `Tempo` | Distributed trace lookup: correlate Discord command → policy decision → dispatch |

**Dual-write audit design (from M12-WP5):** `OTelAuditWriter` writes every audit event to both:
- PostgreSQL (`audit_events` table) — the durable, queryable record for Grafana business panels
- OTel log pipeline — for Loki ingestion and trace correlation

The PostgreSQL write is the primary write (fail-hard, AUD-001 compliant). The OTel write is secondary (fail-soft: logs locally on export error, does not block the audit record). This ordering satisfies the `durable-write-first` governance constraint.

**Alert routing:** Grafana alert rules (in `ops/grafana/provisioning/alerting/`) route threshold alerts to Discord via a webhook contact point (`leadership_council` channel). This keeps Discord as the single interaction surface for operator notifications.

---

## Rationale

| Option | Reason accepted / rejected |
|---|---|
| **Chosen: single provisioned dashboard, dual data source (Postgres + OTel)** | Minimal surface, version-controlled, fits single-operator model. Dual data source gives both query-able business data (Postgres) and trace correlation (OTel). |
| Alternative: multiple role-specific dashboards | Adds complexity for no MVP-v2 benefit. Single operator doesn't need role-specific views. |
| Alternative: dashboard created manually in Grafana UI | Not reproducible. Lost on container restart. Cannot be reviewed or version-controlled. |
| Alternative: OTel pipeline only (no direct Postgres queries) | Grafana's Postgres plugin gives direct SQL access to task/audit data without requiring Loki query language. Simpler for business panels. Loki/Tempo still used for trace and log correlation. |
| Alternative: Separate alert notification channel (email, PagerDuty) | Violates two-surface rule. Discord is the operator interaction surface. |

---

## Consequences

- **Implementation:** `ops/grafana/provisioning/` — datasource YAML files for PostgreSQL, Prometheus, Tempo; alert contact point, notification policy, and rules YAML; `ops/grafana/dashboards/operator-main.json`.
- **Compose:** Grafana service in `compose.yml` gains volume mounts for provisioning directory. `OPENQILIN_OTLP_ENDPOINT` env var required for OTel export from control plane and worker.
- **Governance:** dashboard changes must go through `ops/grafana/` file edits and version control — not Grafana UI. The "two surfaces only" rule is enforced by never adding a third surface here.
- **Observability AUD-001:** PostgreSQL audit_events write is the primary write. Any code path that calls `audit_writer.write()` must fail (not silently succeed) if the PostgreSQL write fails. The OTel export failure is non-blocking.
- **M14 extension point:** the single dashboard will gain budget tracking panels in M14. No structural change to the provisioning approach is anticipated.

---

## References

- Spec: `spec/observability/OperatorDashboardModel.md`, `spec/observability/AuditEvents.md`
- Component delta: `design/v2/components/ObservabilityAndDashboardDelta-v2.md`
- Milestone design: `design/v2/architecture/M12-InfrastructureWiringAndSecurityModuleDesign-v2.md`
- Implementing commit: `cfd0cd5` — feat(m12-wp5): wire OTel export, OTelAuditWriter, and Grafana provisioning
- Related: ADR-0006 (PostgreSQL migration that makes the audit_events table available)
