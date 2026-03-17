# OpenQilin v2 - Implementation Progress

Status: `active`
Updated: `2026-03-16`
Tracking authority: GitHub Issues/PRs are the operational source of truth. This doc is the in-repo WP/milestone-level mirror.

---

## Milestone Status Summary

| Milestone | Status | WPs Done | Notes |
|---|---|---|---|
| M11 | `done` | 4 / 4 | All WPs complete; exit criteria met |
| M12 | `done` | 8 / 8 | All WPs done; PR #88 raised; exit criteria partially met (compose stack validation pending prod) |
| M13 | `planned` | 0 / 8 | Entry gate: M12 complete; milestone tracker #97; WPs #89–#96 |
| M14 | `planned` | 0 / 7 | Entry gate: M13 complete; all remaining agents + file-backed artifact storage |
| M15 | `planned` | 0 / 6 | Entry gate: M14 complete |
| M16 | `planned` | 0 / 5 | Entry gate: M15 complete |
| M17 | `planned` | 0 / 6 | Entry gate: M16 complete |

---

## M11 — Discord Grammar and Secretary Activation

WP document: `05-milestones/M11-WorkPackages-v1.md`

| WP | Title | Status | Issue | PR | Notes |
|---|---|---|---|---|---|
| M11-WP1 | Grammar Layer | `done` | #75 | — | grammar package (4 modules) + discord_ingress wired |
| M11-WP2 | C-7 Security Fix: `chat_class` KeyError | `done` | #76 | — | Fixed in discord_governance.py; 3 unit tests added |
| M11-WP3 | Secretary Agent Activation | `done` | #77 | — | agents/secretary/ package; advisory policy profile; channel membership activated |
| M11-WP4 | LangSmith Dev-Time Tracing | `done` | #78 | — | compose.yml + .env.example updated |

**M11 Exit criteria:** `done`

---

## M12 — Infrastructure Wiring, Security Hardening, and CSO Activation

WP document: `05-milestones/M12-WorkPackages-v1.md`

| WP | Title | Status | Issue | PR | Notes |
|---|---|---|---|---|---|
| M12-WP1 | OPA Policy Runtime Wiring (C-1) | `done` | #80 | #88 | OPAPolicyRuntimeClient + Rego bundle + startup validation; InMemory moved to testing/ |
| M12-WP2 | Obligation Application (C-2) | `done` | #81 | #88 | ObligationDispatcher with 4 handlers; wired into owner_commands for allow_with_obligations |
| M12-WP3 | PostgreSQL Repository Migration | `done` | #82 | #88 | 7 migrations; 7 Postgres repos; H-4/H-5/H-6 fixed |
| M12-WP4 | Redis Idempotency Wiring | `done` | #83 | #88 | RedisIdempotencyCacheStore; env-gated via OPENQILIN_REDIS_URL |
| M12-WP5 | OTel Export Wiring (C-5) | `done` | #84 | #88 | configure_tracer/metrics/logs; OTelAuditWriter dual-write |
| M12-WP6 | Security Hardening: C-6 and C-8 | `done` | #85 | #88 | C-6: DB-backed role resolution; C-8: principal_role in ToolCallContext |
| M12-WP7 | Critical Runtime Bug Fixes: H-1, H-2 | `done` | #86 | #88 | H-1: DispatchTargetError + mark_failed; H-2: transition_guard wired into both repos |
| M12-WP8 | CSO Activation | `done` | #87 | #88 | agents/cso/ package; CSOAgent + assert\_opa\_client\_required; cso in `_INSTITUTIONAL_ROLES`; wired into RuntimeServices |

**M12 Exit criteria:** `done` — all 8 WPs done; PR #88 raised; compose stack validation pending prod verification

---

## M13 — Project Space Binding, Routing, Orchestration, and Agent Spec Fixes

WP document: `05-milestones/M13-WorkPackages-v1.md`

| WP | Title | Status | Issue | PR | Notes |
|---|---|---|---|---|---|
| M13-WP1 | LangGraph Orchestration Adoption (C-9) | `done` | #89 | — | 554 tests pass; all static checks clean |
| M13-WP2 | Loop Controls Enforcement | `pending` | #90 | — | — |
| M13-WP3 | Project Space Binding and Routing | `pending` | #91 | — | — |
| M13-WP4 | H-3 Fix: Snapshot Split-Brain | `pending` | #92 | — | — |
| M13-WP5 | Domain Leader Virtual Agent Activation | `pending` | #93 | — | Entry requires WP7 (CSO rewrite) complete |
| M13-WP6 | Sandbox Enforcement Scaffolding (C-10) | `pending` | #94 | — | — |
| M13-WP7 | CSO Rewrite: Chief Strategy Officer | `pending` | #95 | — | Remove OPA dep; rewrite as portfolio strategy advisor; fix assert_opa_client_required |
| M13-WP8 | Secretary and Routing Spec Alignment | `pending` | #96 | — | Register secretary in _INSTITUTIONAL_ROLES; add CSO to FreeTextRouter; Secretary data access |

**M13 Exit criteria:** `pending`

---

## M14 — Executive and Operational Agent Activation

WP document: `05-milestones/M14-WorkPackages-v1.md`

| WP | Title | Status | Issue | PR | Notes |
|---|---|---|---|---|---|
| M14-WP1 | Project Manager Agent | `pending` | — | — | Status reports/decisions (advisory=deny); completion_report; state-aware writes; Specialist dispatch; DL escalation |
| M14-WP2 | CEO Agent | `pending` | — | — | Directives (advisory=deny); GATE-003/004/005; revision_cycle_count; co-approval enforcement |
| M14-WP3 | CWO Agent | `pending` | — | — | Command authority (decision=deny); reads completion_report before co-approval; project_charter write; full DecisionReviewGates |
| M14-WP4 | Auditor Agent | `pending` | — | — | ESC-005/006 CEO+owner pause notification; project-doc compliance monitoring; behavioral violation path |
| M14-WP5 | Administrator Agent | `pending` | — | — | Artifact caps; hash integrity enforcement; STR/FRM rule bindings; Auditor/Admin boundary clarified |
| M14-WP6 | Specialist Agent and Task Execution Engine | `pending` | — | — | Writes task_execution_results NOT project artifacts (spec conflict resolved); Specialist→DL path |
| M14-WP7 | File-Backed Artifact Storage | `pending` | — | — | Canonical OPENQILIN_SYSTEM_ROOT path; storage_uri + content_hash in DB; ProjectArtifactModel §2.1/§7 |

**M14 Exit criteria:** `pending`

---

## M15 — Budget Persistence, Real Cost Model, and Grafana Dashboard

WP document: `05-milestones/M15-WorkPackages-v1.md`

| WP | Title | Status | Issue | PR | Notes |
|---|---|---|---|---|---|
| M15-WP1 | PostgreSQL Budget Ledger (C-3) | `pending` | — | — | — |
| M15-WP2 | Token-Based Cost Model | `pending` | — | — | — |
| M15-WP3 | Budget Obligation Enforcement | `pending` | — | — | — |
| M15-WP4 | Bug Fixes: M-4 and M-5 | `pending` | — | — | — |
| M15-WP5 | Grafana Dashboard Build | `pending` | — | — | — |
| M15-WP6 | Grafana Alerting and Discord Webhook | `pending` | — | — | — |

**M15 Exit criteria:** `pending`

---

## M16 — Onboarding, Diagnostics, and Runtime Polish

WP document: `05-milestones/M16-WorkPackages-v1.md`

| WP | Title | Status | Issue | PR | Notes |
|---|---|---|---|---|---|
| M16-WP1 | RuntimeSettings Singleton (M-1) | `pending` | — | — | — |
| M16-WP2 | Conversation History Persistence (M-2) | `pending` | — | — | — |
| M16-WP3 | Idempotency Namespace Separation (M-3) | `pending` | — | — | — |
| M16-WP4 | Doctor / Diagnostics CLI | `pending` | — | — | — |
| M16-WP5 | Loop Control Audit and Token Discipline | `pending` | — | — | — |

**M16 Exit criteria:** `pending`

---

## M17 — Open-Source and Sponsorship Readiness

WP document: `05-milestones/M17-WorkPackages-v1.md`

| WP | Title | Status | Issue | PR | Notes |
|---|---|---|---|---|---|
| M17-WP1 | Public README and Repository Clarity | `pending` | — | — | — |
| M17-WP2 | Roadmap | `pending` | — | — | — |
| M17-WP3 | Demo Assets | `pending` | — | — | — |
| M17-WP4 | Contributor Entry Path | `pending` | — | — | — |
| M17-WP5 | Website and Public Presence | `pending` | — | — | — |
| M17-WP6 | Sponsorship and Startup-Credit Readiness | `pending` | — | — | — |

**M17 Exit criteria:** `pending`

---

## Open Blockers

None recorded yet. Update this section as blockers are identified.

---

## Bug Fix Tracking

All 20 architectural review findings from `00-direction/ArchitecturalReviewFindings-v2.md`, mapped to milestone and WP:

| Bug | Description | Milestone | WP | Status |
|---|---|---|---|---|
| C-1 | OPA never contacted | M12 | M12-WP1 | `done` |
| C-2 | Obligations empty placeholder | M12 | M12-WP2 | `done` |
| C-3 | In-memory integer budget counter | M15 | M15-WP1 | `pending` |
| C-5 | OTel export not wired | M12 | M12-WP5 | `done` |
| C-6 | Role self-assertion from header | M12 | M12-WP6 | `done` |
| C-7 | `chat_class` KeyError → 500 | M11 | M11-WP2 | `done` |
| C-8 | Write tool access check inverted | M12 | M12-WP6 | `done` |
| C-9 | LangGraph not used; linear HTTP handler | M13 | M13-WP1 | `resolved` |
| C-10 | Sandbox enforcement empty placeholder | M13 | M13-WP6 | `pending` |
| H-1 | Fail-open dispatch fallback | M12 | M12-WP7 | `done` |
| H-2 | No state transition guard | M12 | M12-WP7 | `done` |
| H-3 | Snapshot split-brain | M13 | M13-WP4 | `pending` |
| H-4 | Dual RuntimeServices init | M12 | M12-WP3 | `done` |
| H-5 | Idempotency re-claim after failure | M12 | M12-WP3 | `done` |
| H-6 | `dispatched` miscounted as terminal | M12 | M12-WP3 | `done` |
| M-1 | Multiple RuntimeSettings instances | M16 | M16-WP1 | `pending` |
| M-2 | Conversation history lost on restart | M16 | M16-WP2 | `pending` |
| M-3 | Idempotency namespace collision | M16 | M16-WP3 | `pending` |
| M-4 | Budget check silently skipped | M15 | M15-WP4 | `pending` |
| M-5 | Agent registry bootstrap overwrites records | M15 | M15-WP4 | `pending` |

---

## Update Protocol

Update this document when:
- a WP changes status (`pending → in_progress → done`)
- a milestone changes status
- a new blocker is identified or resolved
- a bug fix is completed

Cross-reference the corresponding WP document task checkbox and GitHub issue/PR.
