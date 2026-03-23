# OpenQilin MVP-v2 Milestone Plan

Date: `2026-03-16`
Status: `active`
Supersedes: `00-direction/TemporaryMvpPlan-v2.md`

---

## 1. Goal

MVP-v2 gives one solopreneur a repeatable, trustworthy way to run projects through Discord — lower setup friction, lower coordination noise, and honest cost and governance visibility. It closes the gap between what OpenQilin claims in spec and what it actually enforces at runtime, and leaves the project ready for public introduction.

Full success bar: `00-direction/MvpV2SuccessCriteria-v1.md`

---

## 2. Milestone Overview

| ID | Milestone | Status | Gate (entry) | Exit criteria |
|---|---|---|---|---|
| M11 | Discord Grammar and Secretary Activation | `done` | M10 complete | Free-text + `/oq` command UX live; Secretary active; C-7 fixed |
| M12 | Infrastructure Wiring, Security Hardening, CSO Activation | `done` | M11 complete | OPA, PostgreSQL, Redis, OTel all wired; all C/H security fixes applied; CSO wired |
| M13 | Project Space Binding, Routing, Orchestration, and Agent Spec Fixes | `done` | M12 complete | LangGraph active; project spaces bound; DL virtual agent active; H-3 fixed; CSO rewritten as Chief Strategy Officer; Secretary spec aligned |
| M14 | Executive and Operational Agent Activation | `done` | M13 complete | PM, CEO, CWO, Auditor, Administrator, Specialist agents active; DecisionReviewGates flow wired |
| M15 | Budget Persistence, Real Cost Model, and Grafana Dashboard | `done` | M14 complete | PostgreSQL budget ledger live; token cost model active; Grafana dashboard provisioned with 6 panels |
| M16 | Onboarding, Diagnostics, and Runtime Polish | `done` | M15 complete | RuntimeSettings singleton; conversation persistence; idempotency namespaced; doctor CLI working |
| M17 | Open-Source and Sponsorship Readiness | `planned` | M16 complete | README, demo, roadmap, website, contributor path, sponsorship assets all published |

---

## 3. Sequencing Rationale

**M11 before M12:** Chat UX and Secretary can be delivered using existing InMemory policy stubs (Secretary is advisory-only; no mutation authority). C-7 is a surface-level fix with no infrastructure dependency.

**M12 pulled forward (before agent features):** All subsequent milestones depend on real infrastructure. OPA, PostgreSQL, and OTel must be live before new agent roles can claim real governance authority. Role self-assertion (C-6) must be fixed before CSO or Secretary are trusted with enforcement. Infrastructure must be honest before dashboard panels have real data.

**M13 after M12:** LangGraph orchestration and project-space automation require real PostgreSQL task state. Domain Leader escalation flows require real policy evaluation from M12 OPA. M13 also fixes the CSO implementation (wrong domain in M12) and aligns Secretary spec gaps before agent activation in M14.

**M14 after M13:** All executive and operational agents (PM, CEO, CWO, Auditor, Administrator, Specialist) require LangGraph orchestration (M13-WP1), project-space routing (M13-WP3), and a correctly implemented CSO (M13-WP7) before the DecisionReviewGates approval flow and workforce lifecycle can be wired.

**M15 after M14:** Grafana budget and cost panels need real PostgreSQL budget data and real task execution from M14 agents. Budget obligation enforcement requires LangGraph nodes from M13.

**M16 after M15:** Runtime polish is low-risk cleanup with all infrastructure and agents stable. RuntimeSettings singleton and conversation persistence are safe to ship last.

**M17 after M16:** Public-readiness requires a complete, polished runtime to demo.

---

## 4. Cross-Cutting Constraints

These apply to every milestone:

| Constraint | Rule |
|---|---|
| No new roles on mock policy | DL MUST NOT be activated until `OPAPolicyRuntimeClient` is active (M12). CSO is advisory (no OPA needed); CEO/CWO/PM/Auditor/Administrator/Specialist activated in M14 after real infrastructure is stable. |
| Infrastructure before features | Grafana panels must have real PostgreSQL data; budget panels must have real budget ledger |
| LangGraph before multi-step flows | DL escalation, DecisionReviewGates approval flow, and multi-hop agent interactions require LangGraph from M13 |
| Fail-closed default | Every new code path defaults to deny/block/error on unknown or error state |
| Two surfaces only | Discord (interaction) and Grafana (visualization) — no third UI surface in MVP-v2 |
| Durable-write-first | Governance-critical events written to PostgreSQL before OTel export; never the reverse |

---

## 5. Bug Fix Reference Map

All bug fixes from the 2026-03-15 architectural review, mapped to milestone:

| Bug | Description | Milestone | WP |
|---|---|---|---|
| C-1 | OPA never contacted; InMemory policy client in prod | M12 | M12-WP1 |
| C-2 | `obligations.py` empty placeholder; `allow_with_obligations` → unconditional allow | M12 | M12-WP2 |
| C-3 | In-memory integer budget counter; no atomicity (BUD-002 violation) | M14 | M14-WP1 |
| C-5 | OTel export not wired; three observability modules write to Python lists only | M12 | M12-WP5 |
| C-6 | Role self-assertion: role from HTTP header, not identity mapping | M12 | M12-WP6 |
| C-7 | `chat_class` KeyError → 500 in `discord_governance.py` | M11 | M11-WP2 |
| C-8 | Write tool access check inverted: checks `recipient_role` not `principal_role` | M12 | M12-WP6 |
| C-9 | LangGraph declared but not used; all orchestration is a linear HTTP handler | M13 | M13-WP1 |
| C-10 | `enforcement.py` empty placeholder; no sandbox isolation applied | M13 | M13-WP5 |
| H-1 | Unknown dispatch target silently marked as `dispatched` (fail-open) | M12 | M12-WP7 |
| H-2 | No state transition guard; any string accepted as next status | M12 | M12-WP7 |
| H-3 | Snapshot split-brain: in-memory mutated before disk write succeeds | M13 | M13-WP4 |
| H-4 | Dual `RuntimeServices` init: two separate in-memory instances can exist | M12 | M12-WP7 |
| H-5 | Idempotency re-claim blocked after `failed`/`cancelled` tasks on recovery | M12 | M12-WP7 |
| H-6 | `dispatched` miscounted as terminal in startup recovery | M12 | M12-WP7 |
| M-1 | Multiple independent `RuntimeSettings()` instances per request | M15 | M15-WP1 |
| M-2 | `InMemoryConversationStore` loses all context on restart | M15 | M15-WP2 |
| M-3 | Idempotency key namespace collision between ingress and communication layers | M15 | M15-WP3 |
| M-4 | Budget check silently skipped when client is `None` | M14 | M14-WP4 |
| M-5 | Agent registry bootstrap overwrites existing records on every startup | M14 | M14-WP4 |

---

## 6. Work Package Documents

| Milestone | WP Document |
|---|---|
| M11 | `M11-WorkPackages-v1.md` |
| M12 | `M12-WorkPackages-v1.md` |
| M13 | `M13-WorkPackages-v1.md` |
| M14 | `M14-WorkPackages-v1.md` |
| M15 | `M15-WorkPackages-v1.md` |
| M16 | `M16-WorkPackages-v1.md` |
| M17 | `M17-WorkPackages-v1.md` |

---

## 7. Supporting Artifacts

| Artifact | Location | Role |
|---|---|---|
| Success criteria | `00-direction/MvpV2SuccessCriteria-v1.md` | Definition of done for MVP-v2 as a whole |
| Architecture delta | `00-direction/MvpV2ArchitectureDelta-v1.md` | Keep/refactor/replace/defer by component |
| Improvement backlog | `00-direction/TemporaryImprovementPoints-v2.md` | Exhaustive finding list with file/line references |
| Design ADRs | `design/v2/adr/` | Architectural decisions (OPA, LangGraph, PostgreSQL migration, Grafana) |
| Component deltas | `design/v2/components/` | Implementation guidance per component |
| Module designs | `design/v2/architecture/` | Package layout, interfaces, and test focus per milestone |

---

## 8. Milestone Completion Protocol

Each milestone is complete when:
1. All WPs in the milestone's WP document are marked `done`.
2. All WP done-criteria pass in a full compose stack (not InMemory substitutes).
3. Integration tests cover the critical path added in the milestone.
4. No new `InMemory*` placeholder is introduced in a production code path.
5. The milestone exit criteria in §2 are demonstrably met.
