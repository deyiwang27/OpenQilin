# OpenQilin v2 — Design Artifacts

## 1. Purpose
This directory contains the implementation-layer design artifacts for MVP-v2. It translates the v2 direction decisions in `implementation/v2/planning/` and the v2 spec additions in `spec/` into concrete implementation guidance.

Design artifacts do not replace the spec. They bridge spec contracts to code: package layouts, integration topology, key interfaces, failure modes, and test focus areas.

Normative precedence:
1. `constitution/`
2. `spec/`
3. `design/` (this directory)

## 2. MVP-v2 Milestone Index

| Milestone | Theme | Primary Design Docs |
|---|---|---|
| M11 | Discord surface, chat grammar, Secretary activation | `architecture/M11-DiscordGrammarAndSecretaryModuleDesign-v2.md`, `components/ControlPlaneComponentDelta-v2.md` |
| M12 | Infrastructure wiring, security hardening, CSO activation | `architecture/M12-InfrastructureWiringAndSecurityModuleDesign-v2.md`, `components/PolicyRuntimeComponentDelta-v2.md` |
| M13 | Project space binding, LangGraph adoption, Domain Leader activation | `architecture/M13-ProjectSpaceAndOrchestrationModuleDesign-v2.md`, `components/OrchestratorComponentDelta-v2.md` |
| M14 | Budget persistence, real cost model, Grafana dashboard | `architecture/M14-BudgetAndDashboardModuleDesign-v2.md`, `components/ObservabilityAndDashboardDelta-v2.md`, `components/BudgetRuntimeComponentDelta-v2.md` |
| M15 | Onboarding, diagnostics, runtime polish | `architecture/M15-RuntimePolishModuleDesign-v2.md` |

## 3. Architectural Decision Records

| ADR | Decision | Milestone |
|---|---|---|
| ADR-0004 | OPA HTTP client integration (replacing InMemoryPolicyRuntimeClient) | M12 |
| ADR-0005 | LangGraph state machine adoption (replacing linear HTTP handler orchestration) | M13 |
| ADR-0006 | PostgreSQL repository migration strategy (replacing all InMemory repositories) | M12 |
| ADR-0007 | Grafana as single operator dashboard covering business + ops data | M14 |

## 4. Relationship to v1 Design

v2 design artifacts are **deltas**, not rewrites. The v1 design documents in `design/v1/` remain authoritative for components not explicitly modified by v2. v2 component delta documents describe only what changes; unchanged behavior inherits from the v1 component design.

## 5. Key Constraints Carried Forward from v1

- Normative precedence: `constitution/` > `spec/` > `design/`
- Governance-core gate order: validate identity → policy decision → obligations → budget reservation → dispatch → observability
- Fail-closed posture: unknown/error states deny before dispatching
- Durable append-first for governance-critical events before async export

## 6. v2-Specific Design Principles

- **Infrastructure before features**: OPA, PostgreSQL, and OTel wiring (M12) must complete before new agent roles or dashboard panels are considered reliable.
- **No new roles on mock policy**: CSO and Domain Leader MUST NOT be activated until real OPA enforcement is in place.
- **LangGraph before multi-step workflows**: Adopt LangGraph in M13 before wiring CSO policy gates, DL escalations, or multi-hop approval flows.
- **Two surfaces only**: Discord (interaction) and Grafana (visualization). No additional UI surface in MVP-v2.
