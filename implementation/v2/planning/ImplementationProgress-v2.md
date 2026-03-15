# OpenQilin v2 - Implementation Progress

Status: `active`
Updated: `2026-03-15`
Tracking authority: GitHub Issues/PRs are the operational source of truth. This doc is the in-repo WP/milestone-level mirror.

---

## Milestone Status Summary

| Milestone | Status | WPs Done | Notes |
|---|---|---|---|
| M11 | `planned` | 0 / 4 | Entry gate: M10 complete |
| M12 | `planned` | 0 / 8 | Entry gate: M11 complete |
| M13 | `planned` | 0 / 6 | Entry gate: M12 complete |
| M14 | `planned` | 0 / 6 | Entry gate: M13 complete |
| M15 | `planned` | 0 / 5 | Entry gate: M14 complete |
| M16 | `planned` | 0 / 6 | Entry gate: M15 complete |

---

## M11 — Discord Grammar and Secretary Activation

WP document: `05-milestones/M11-WorkPackages-v1.md`

| WP | Title | Status | Issue | PR | Notes |
|---|---|---|---|---|---|
| M11-WP1 | Grammar Layer | `pending` | — | — | — |
| M11-WP2 | C-7 Security Fix: `chat_class` KeyError | `pending` | — | — | — |
| M11-WP3 | Secretary Agent Activation | `pending` | — | — | — |
| M11-WP4 | LangSmith Dev-Time Tracing | `pending` | — | — | — |

**M11 Exit criteria:** `pending`

---

## M12 — Infrastructure Wiring, Security Hardening, and CSO Activation

WP document: `05-milestones/M12-WorkPackages-v1.md`

| WP | Title | Status | Issue | PR | Notes |
|---|---|---|---|---|---|
| M12-WP1 | OPA Policy Runtime Wiring (C-1) | `pending` | — | — | — |
| M12-WP2 | Obligation Application (C-2) | `pending` | — | — | — |
| M12-WP3 | PostgreSQL Repository Migration | `pending` | — | — | — |
| M12-WP4 | Redis Idempotency Wiring | `pending` | — | — | — |
| M12-WP5 | OTel Export Wiring (C-5) | `pending` | — | — | — |
| M12-WP6 | Security Hardening: C-6 and C-8 | `pending` | — | — | — |
| M12-WP7 | Critical Runtime Bug Fixes: H-1, H-2 | `pending` | — | — | — |
| M12-WP8 | CSO Activation | `pending` | — | — | — |

**M12 Exit criteria:** `pending`

---

## M13 — Project Space Binding, Routing, and Orchestration Foundation

WP document: `05-milestones/M13-WorkPackages-v1.md`

| WP | Title | Status | Issue | PR | Notes |
|---|---|---|---|---|---|
| M13-WP1 | LangGraph Orchestration Adoption (C-9) | `pending` | — | — | — |
| M13-WP2 | Loop Controls Enforcement | `pending` | — | — | — |
| M13-WP3 | Project Space Binding and Routing | `pending` | — | — | — |
| M13-WP4 | H-3 Fix: Snapshot Split-Brain | `pending` | — | — | — |
| M13-WP5 | Domain Leader Virtual Agent Activation | `pending` | — | — | — |
| M13-WP6 | Sandbox Enforcement Scaffolding (C-10) | `pending` | — | — | — |

**M13 Exit criteria:** `pending`

---

## M14 — Budget Persistence, Real Cost Model, and Grafana Dashboard

WP document: `05-milestones/M14-WorkPackages-v1.md`

| WP | Title | Status | Issue | PR | Notes |
|---|---|---|---|---|---|
| M14-WP1 | PostgreSQL Budget Ledger (C-3) | `pending` | — | — | — |
| M14-WP2 | Token-Based Cost Model | `pending` | — | — | — |
| M14-WP3 | Budget Obligation Enforcement | `pending` | — | — | — |
| M14-WP4 | Bug Fixes: M-4 and M-5 | `pending` | — | — | — |
| M14-WP5 | Grafana Dashboard Build | `pending` | — | — | — |
| M14-WP6 | Grafana Alerting and Discord Webhook | `pending` | — | — | — |

**M14 Exit criteria:** `pending`

---

## M15 — Onboarding, Diagnostics, and Runtime Polish

WP document: `05-milestones/M15-WorkPackages-v1.md`

| WP | Title | Status | Issue | PR | Notes |
|---|---|---|---|---|---|
| M15-WP1 | RuntimeSettings Singleton (M-1) | `pending` | — | — | — |
| M15-WP2 | Conversation History Persistence (M-2) | `pending` | — | — | — |
| M15-WP3 | Idempotency Namespace Separation (M-3) | `pending` | — | — | — |
| M15-WP4 | Doctor / Diagnostics CLI | `pending` | — | — | — |
| M15-WP5 | Loop Control Audit and Token Discipline | `pending` | — | — | — |

**M15 Exit criteria:** `pending`

---

## M16 — Open-Source and Sponsorship Readiness

WP document: `05-milestones/M16-WorkPackages-v1.md`

| WP | Title | Status | Issue | PR | Notes |
|---|---|---|---|---|---|
| M16-WP1 | Public README and Repository Clarity | `pending` | — | — | — |
| M16-WP2 | Roadmap | `pending` | — | — | — |
| M16-WP3 | Demo Assets | `pending` | — | — | — |
| M16-WP4 | Contributor Entry Path | `pending` | — | — | — |
| M16-WP5 | Website and Public Presence | `pending` | — | — | — |
| M16-WP6 | Sponsorship and Startup-Credit Readiness | `pending` | — | — | — |

**M16 Exit criteria:** `pending`

---

## Open Blockers

None recorded yet. Update this section as blockers are identified.

---

## Bug Fix Tracking

All 20 architectural review findings from `00-direction/ArchitecturalReviewFindings-v2.md`, mapped to milestone and WP:

| Bug | Description | Milestone | WP | Status |
|---|---|---|---|---|
| C-1 | OPA never contacted | M12 | M12-WP1 | `pending` |
| C-2 | Obligations empty placeholder | M12 | M12-WP2 | `pending` |
| C-3 | In-memory integer budget counter | M14 | M14-WP1 | `pending` |
| C-5 | OTel export not wired | M12 | M12-WP5 | `pending` |
| C-6 | Role self-assertion from header | M12 | M12-WP6 | `pending` |
| C-7 | `chat_class` KeyError → 500 | M11 | M11-WP2 | `pending` |
| C-8 | Write tool access check inverted | M12 | M12-WP6 | `pending` |
| C-9 | LangGraph not used; linear HTTP handler | M13 | M13-WP1 | `pending` |
| C-10 | Sandbox enforcement empty placeholder | M13 | M13-WP6 | `pending` |
| H-1 | Fail-open dispatch fallback | M12 | M12-WP7 | `pending` |
| H-2 | No state transition guard | M12 | M12-WP7 | `pending` |
| H-3 | Snapshot split-brain | M13 | M13-WP4 | `pending` |
| H-4 | Dual RuntimeServices init | M12 | M12-WP3 | `pending` |
| H-5 | Idempotency re-claim after failure | M12 | M12-WP3 | `pending` |
| H-6 | `dispatched` miscounted as terminal | M12 | M12-WP3 | `pending` |
| M-1 | Multiple RuntimeSettings instances | M15 | M15-WP1 | `pending` |
| M-2 | Conversation history lost on restart | M15 | M15-WP2 | `pending` |
| M-3 | Idempotency namespace collision | M15 | M15-WP3 | `pending` |
| M-4 | Budget check silently skipped | M14 | M14-WP4 | `pending` |
| M-5 | Agent registry bootstrap overwrites records | M14 | M14-WP4 | `pending` |

---

## Update Protocol

Update this document when:
- a WP changes status (`pending → in_progress → done`)
- a milestone changes status
- a new blocker is identified or resolved
- a bug fix is completed

Cross-reference the corresponding WP document task checkbox and GitHub issue/PR.
