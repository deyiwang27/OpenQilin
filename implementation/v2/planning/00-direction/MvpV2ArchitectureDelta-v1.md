# OpenQilin MVP-v2 Architecture Delta

Date: `2026-03-14`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Describe the architectural delta from MVP-v1 to MVP-v2.
- Make the refactor scope explicit enough to support milestone planning.
- Distinguish what should be kept, replaced, simplified, and deferred.

## 2. Design Intent

MVP-v2 is not a ground-up rewrite.

It is a focused refactor that should:
- preserve OpenQilin's governance-first product identity
- simplify the Discord operating model
- make runtime behavior more honest and integrated
- improve operator visibility and cost discipline
- reduce mismatch between planning claims and actual wiring

## 3. What v1 Already Proves

MVP-v1 already proves useful foundation pieces:
- owner-command ingress with active governance and policy gates
- governed project lifecycle flows
- institutional role model
- basic Discord integration and identity/channel governance
- grounded read/write tool flows
- budget and policy fail-closed shells
- runtime state and observability scaffolding

These should be treated as assets, not discarded casually.

## 4. What MVP-v2 Must Change

### 4.1 Interaction model

From:
- JSON-shaped daily Discord interaction

To:
- free-text plus compact command interaction

### 4.2 Discord execution surface

From:
- multi-bot role sprawl for project interaction

To:
- stable institutional bot layer plus project spaces with virtual PM/DL routing

### 4.3 Project identity model

From:
- project communication partially tied to Discord bot identity assumptions

To:
- explicit project-space binding and runtime-owned project context

### 4.4 Visibility model

From:
- chat-first with limited operator visibility

To:
- Discord-first conversation plus Grafana as the single dashboard for all visualization (business + ops + budget + governance)
- no separate dashboard app or React console in MVP-v2
- Grafana reads business data from PostgreSQL and telemetry from OpenTelemetry; Grafana alerting pushes threshold notifications to Discord via webhook

### 4.5 Runtime truthfulness

From:
- several placeholder or in-memory shells presented alongside broader architecture claims

To:
- clearer, more honest topology with real critical-path wiring where it matters

## 5. Keep / Refactor / Replace / Defer

### 5.1 Keep

- governance-first product thesis
- institutional role separation
- project lifecycle model
- fail-closed posture
- audit and metric intent
- grounded tool access posture
- Secretary as advisory front door

### 5.2 Refactor

- Discord routing
- owner command UX
- project communication model
- budget and policy runtime wiring
- dashboard/operator visibility layer
- runtime state boundaries and persistence claims

### 5.3 Replace

- project-scoped role bots as the main scaling model
- JSON as the normal operator UX
- shell-level assumptions that stand in for real runtime behavior on critical paths

### 5.4 Defer

- broad multi-channel support beyond Discord
- full OpenQilin-owned console as the primary product surface
- large ecosystem/plugin marketplace behavior
- advanced exposed domain-leader participation in owner-facing chat

## 6. Proposed MVP-v2 Architectural Shape

### 6.1 Surface layer

- Discord as primary interaction surface
- lightweight dashboard as secondary operator surface

### 6.2 Adapter layer

- Discord adapter normalizes inbound events into runtime envelopes
- future adapters should target the same normalized ingress model

### 6.3 Binding and routing layer

- conversation/project-space binding becomes first-class
- routing resolves by chat class, project context, mentions, and default recipient

### 6.4 Governance layer

- active governance and policy checks stay on the critical path
- constitution and budget shells should move toward real runtime authority

### 6.5 Execution layer

- PM coordinates downstream project work
- DL and specialists remain behind PM by default
- tool and skill bindings become registry-driven instead of partly hardcoded

### 6.6 Visibility layer

- Grafana is the single dashboard; it reads business data (projects, budget, audit events, governance state) from PostgreSQL and telemetry (agent health, LLM latency, error rates) from OpenTelemetry
- Grafana alerting routes threshold notifications to Discord via webhook; the owner observes in Grafana and acts in Discord
- Secretary summaries and severity-based alerts integrate with `leadership_council` as the shared leadership surface
- no separate React app or lightweight HTML page in MVP-v2; the two surfaces are Discord and Grafana only

## 7. Major Refactor Streams

### 7.1 Discord surface redesign
- institutional/shared/project surface cleanup
- project-space automation
- pinned dashboard link and alert posture

### 7.2 Chat grammar redesign
- free-text parser
- compact command grammar
- routing-aware message interpretation

### 7.3 Project-space binding implementation
- binding model
- persistence
- lifecycle handling
- recovery behavior

### 7.4 Visibility and dashboard implementation
- Grafana as the single dashboard (no separate app)
- PostgreSQL data source for business panels: owner inbox, projects overview, project detail, budget/cost, audit log
- OpenTelemetry data source for ops panels: system health, agent liveness, LLM latency, error rates
- Grafana alerting → Discord webhook for threshold notifications

### 7.5 Runtime integration cleanup
- remove or implement no-op workers
- reduce placeholder execution claims
- clarify persistence and external service boundaries

### 7.6 Governance and budget runtime strengthening
- constitution binding
- budget management fidelity
- testable active runtime enforcement

## 8. Recommended MVP-v2 Milestone Logic

A reasonable milestone sequence is:

1. M11 — interaction and Discord surface simplification, Secretary activation, LangSmith dev tracing
2. M12 — infrastructure wiring (PostgreSQL, OPA, Redis) and CSO activation; must precede dashboard and governance work
3. M13 — project-space binding and routing, Domain Leader virtual activation
4. M14 — budget persistence and Grafana dashboard (single visibility surface: business + ops)
5. M15 — onboarding, diagnostics, and cost discipline
6. M16 — public-readiness and community-facing packaging

Infrastructure wiring (M12) is pulled forward ahead of dashboard and governance milestones because the Grafana business panels and real policy enforcement both depend on PostgreSQL and OPA being live. Building operator visibility on in-memory state would repeat the v1 honesty gap.

## 9. Architecture Risks

### 9.1 Scope inflation
- Discord redesign, dashboarding, and runtime cleanup can become a rewrite if not bounded.

### 9.2 Surface split confusion
- Without a clear Discord-vs-dashboard boundary, operator experience may become fragmented.

### 9.3 Runtime honesty gap
- If v2 repeats the pattern of documented architecture outrunning actual wiring, trust will suffer again.

### 9.4 Cost-control regression
- More flexible routing and richer UI can increase token and complexity overhead if not disciplined.

### 9.5 Governance thesis depends entirely on OPA being real [C-1]
- Every authority boundary, policy rule, and governance claim in the constitution assumes OPA is the enforcement point.
- Until OPA is wired (`InMemoryPolicyRuntimeClient` → real OPA HTTP client → `localhost:8181`), the entire governance model is a documentation artifact.
- New agent roles (CSO, Secretary, Domain Leader) must not be activated until real OPA enforcement is in place; adding roles to a mock policy engine only widens the claim-reality gap.

### 9.6 Grafana dashboard strategy is undermined by missing PostgreSQL [C-3, C-5]
- The v2 dashboard strategy depends on Grafana reading business data (projects, budget, governance events, audit trail) from PostgreSQL.
- Until PostgreSQL repositories are wired and OTel export is connected, Grafana can only show infrastructure metrics — not project state, cost, owner inbox, or governance activity.
- The two-surface model (Discord + Grafana) only delivers its value after the persistence gap is closed.

### 9.7 Adding new agent roles before LangGraph creates unbounded coupling [C-9]
- Orchestration currently lives entirely within the HTTP request handler as a linear synchronous call chain.
- As CSO gates, DL escalations, and multi-hop approvals are added, request-coupled orchestration will become unmaintainable and untestable.
- LangGraph adoption must precede the activation of new multi-step role workflows; wiring more roles into the current imperative path is the wrong direction.

### 9.8 Role self-assertion must be fixed before CSO and Secretary activation [C-6]
- The actor role is currently taken directly from the `x-openqilin-actor-role` HTTP header with no cryptographic binding.
- Any caller with a valid connector secret can impersonate any role, including `owner`, `cso`, or `secretary`.
- Activating new governance roles while this vulnerability exists negates any authority boundary the constitution defines.

## 10. Implementation Guidance

For MVP-v2, architectural decisions should be evaluated by three questions:

1. Does this reduce coordination burden for the solopreneur?
2. Does this make authority, budget, and evidence more visible and trustworthy?
3. Does this reduce the gap between how OpenQilin is described and how it actually runs?

If the answer is no to most of these, it is probably not core to MVP-v2.
