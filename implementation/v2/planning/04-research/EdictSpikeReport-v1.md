# Edict Review and OpenQilin Comparison Spike

Date: `2026-03-14`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Review the current upstream implementation posture of `cft0808/edict`.
- Compare Edict with OpenQilin in product and architecture terms.
- Extract useful lessons for OpenQilin MVP-v2 planning without inheriting Edict's product assumptions blindly.

## 2. Scope and Sources

Primary Edict sources reviewed:
- GitHub repo root: https://github.com/cft0808/edict
- English README: https://github.com/cft0808/edict/blob/main/README_EN.md
- roadmap: https://github.com/cft0808/edict/blob/main/ROADMAP.md
- architecture note: https://github.com/cft0808/edict/blob/main/edict_agent_architecture.md
- task dispatch architecture: https://github.com/cft0808/edict/blob/main/docs/task-dispatch-architecture.md
- installer: https://github.com/cft0808/edict/blob/main/install.sh
- backend requirements: https://github.com/cft0808/edict/blob/main/edict/backend/requirements.txt
- backend app entry: https://github.com/cft0808/edict/blob/main/edict/backend/app/main.py
- dispatch worker: https://github.com/cft0808/edict/blob/main/edict/backend/app/workers/dispatch_worker.py
- event bus: https://github.com/cft0808/edict/blob/main/edict/backend/app/services/event_bus.py

Primary OpenQilin sources referenced:
- [TemporaryMvpPlan-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryMvpPlan-v2.md)
- [TemporaryImprovementPoints-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryImprovementPoints-v2.md)
- [LlmProfileBindingModel-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/02-architecture/LlmProfileBindingModel-v2.md)
- [MvpCoreGovernance-v1.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v1/mvp/MvpCoreGovernance-v1.md)
- [discord_governance.py](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/src/openqilin/control_plane/identity/discord_governance.py)

Point-in-time observation for Edict:
- local review clone head: `76e0c102ed1fd9bb541ec130fd1aa5eaa9300517`
- head date: `2026-03-05`

## 3. Executive Summary

Edict is the closest external reference so far to OpenQilin's organizational instincts, but it is not the same product.

Edict is best understood as:
- an OpenClaw-native orchestration layer
- wrapped in a strong institutional metaphor
- with a dashboard-heavy control and observability surface
- and a more formal task state machine than typical agent demos

Product-wise:
- Edict is much closer to OpenQilin than OpenClaw is.
- It cares about review gates, dispatch, task flow, and observability.
- But it is still centered on a generalized multi-agent bureaucracy, not on the solopreneur operator model that now defines OpenQilin.

Architecture-wise:
- Edict is a hybrid.
- The execution substrate is OpenClaw.
- The orchestration and UI layer are Edict-owned.
- This gives Edict speed and leverage, but also creates coupling, duplicated control logic, and setup complexity.

The practical conclusion is:
- OpenQilin should learn from Edict's orchestration visibility, task pipeline design, and event-driven instrumentation.
- OpenQilin should not copy Edict's dependency shape, metaphor-first product identity, or OpenClaw-coupled runtime model.

## 4. Edict Implementation Summary

### 4.1 Product shape

Edict presents itself as a "Three Departments & Six Ministries" multi-agent system inspired by imperial governance. The README emphasizes:
- 12 specialized agents
- built-in review and veto
- real-time dashboard
- intervention controls
- full audit trail
- per-agent model switching
- skill management

This is much more organization-shaped than OpenClaw's personal-assistant framing.

### 4.2 Runtime shape

The current repo is not just prompts and docs. It includes:
- a FastAPI backend
- Redis Streams event bus
- Postgres/SQLAlchemy persistence
- worker processes for orchestration and dispatch
- a React dashboard
- legacy/local dashboard compatibility code

This means Edict is already moving beyond a thin wrapper. It is building a real control surface around an underlying agent runtime.

### 4.3 OpenClaw dependency model

Edict still depends deeply on OpenClaw:
- the installer provisions `~/.openclaw/workspace-*`
- it patches `openclaw.json`
- dispatch calls shell out to `openclaw agent --agent ...`
- dashboard and sync scripts inspect OpenClaw runtime/session artifacts

So Edict is not a standalone orchestration platform yet. It is a higher-level operating model layered on top of OpenClaw.

### 4.4 Task and orchestration model

Edict's strongest implementation idea is its explicit task pipeline:
- task creation
- state transitions
- review/approval loop
- assignment/dispatch
- execution
- completion
- intervention and recovery

This is backed by:
- typed task states
- emitted events
- durable stream-based dispatch
- worker-based orchestration
- replayable-ish audit surfaces

That is materially closer to OpenQilin's intended project/governance posture than OpenClaw is.

### 4.5 Observability posture

Edict invests heavily in operator visibility:
- kanban/task board
- event and activity streams
- live status views
- model config panel
- skills management
- session monitoring

This is one of its clearest strengths. It treats orchestration as something the operator should be able to inspect and intervene in, not just trust blindly.

### 4.6 Implementation drift and consistency issues

One important warning sign: the public marketing layer and the current implementation layer are not fully aligned.

Example:
- README markets `Zero Deps / stdlib only`
- actual backend requirements include `fastapi`, `sqlalchemy`, `asyncpg`, `redis`, `alembic`, and more

This does not make the repo weak, but it does signal architecture transition and messaging drift. For OpenQilin, that is a reminder to keep product promises tightly aligned with what is actually running.

## 5. Product Comparison

### 5.1 Core product thesis

Edict:
- institutionalized multi-agent command system
- general task orchestration under a historical bureaucracy metaphor
- operator-facing dashboard and intervention

OpenQilin:
- built for the solopreneur
- turns one capable person into a coordinated AI-augmented team
- governed role delegation, project-centered execution, and explicit control over authority, budget, and evidence

Assessment:
- Edict and OpenQilin overlap in organizational form.
- OpenQilin has the sharper product thesis.
- Edict feels like a framework/product hybrid.
- OpenQilin has the opportunity to be a more focused operating system for one real operator.

### 5.2 Target user

Edict:
- power users who want to run a visible multi-agent organization
- users who tolerate more system metaphor and setup weight
- likely technical operators drawn to orchestration and dashboards

OpenQilin:
- solopreneurs
- founder-operators
- users who need leverage, not theater
- users who care about trust, clarity, and work outcomes

Assessment:
- Edict's audience is adjacent, but broader and more demo-oriented.
- OpenQilin's ICP is narrower and more commercially coherent.

### 5.3 User experience posture

Edict strengths:
- stronger observability than OpenQilin today
- more explicit operator control panels
- better surfaced task pipeline
- richer live dashboard story

Edict weaknesses:
- metaphor-heavy mental model
- still inherits OpenClaw setup and environment complexity
- control is visible, but authority/budget/evidence governance is thinner than OpenQilin's direction
- product identity may feel more like a multi-agent showcase than a focused operating tool

OpenQilin strengths:
- clearer thesis around solopreneur leverage
- stronger governance framing
- better conceptual fit for controlled delegation

OpenQilin weaknesses versus Edict:
- weaker operator dashboard and observability today
- less ergonomic orchestration surface
- less mature live intervention tooling

### 5.4 Channel and human interaction model

Edict:
- inherits OpenClaw's broader transport model
- appears oriented toward multiple chat surfaces
- uses OpenClaw runtime channels plus dashboard control

OpenQilin:
- currently Discord-centered
- moving toward project-space routing, hybrid chat/command UX, and virtual PM/DL roles

Assessment:
- Edict has more channel breadth through OpenClaw.
- OpenQilin's Discord-first MVP-v2 focus is still the right choice for scope control.
- Longer term, OpenQilin should aim for adapter portability, but not at the cost of product clarity now.

## 6. Architectural Comparison

### 6.1 Core architecture center

Edict:
- orchestration/dashboard layer over OpenClaw runtime
- event bus and task state machine as the organizing backbone
- agent execution delegated to external CLI/runtime

OpenQilin:
- governance/control plane first
- runtime roles, authority, lifecycle, and evidence contracts are central
- chat surfaces should attach to governed bindings, not define the system

Assessment:
- Edict starts from task orchestration and operator visibility.
- OpenQilin starts from constitutional governance and controlled delegation.
- These are compatible ideas, but not identical centers of gravity.

### 6.2 Dependency shape

Edict:
- depends on OpenClaw as execution substrate
- also adds its own backend/database/bus/dashboard stack
- ends up with a layered and relatively heavy system

OpenQilin:
- owns more of its own governance model directly
- currently has less infrastructure breadth
- has the chance to avoid double-stack complexity if v2 refactors stay deliberate

Recommendation:
- OpenQilin should not reproduce Edict's "platform on top of platform" shape unless absolutely necessary.

### 6.3 Eventing and orchestration

Edict:
- Redis Streams-based event bus
- worker recovery via pending claim/ACK
- explicit orchestration worker and dispatch worker
- state transitions as first-class runtime events

OpenQilin:
- has stronger role/governance semantics
- but should learn from Edict's explicit orchestration/event instrumentation

This is one of the best architectural references in Edict.

### 6.4 Observability and intervention

Edict:
- makes live operations visible
- supports stop/cancel/resume style intervention
- treats task progress and audit surfaces as product features

OpenQilin:
- has the right governance idea
- still needs stronger operational visibility and intervention UX in v2

This is a real gap and a useful lesson.

### 6.5 Identity and authority model

Edict:
- has a permission matrix and institutional flow order
- but the authority model is mostly operational/orchestration-oriented
- budget/evidence/governed mutation semantics are not the visible core

OpenQilin:
- aims for explicit authority, budget, evidence, and controlled role delegation
- this is the stronger long-term differentiator

Recommendation:
- borrow Edict's task orchestration mechanics, not its thinner governance semantics.

## 7. What OpenQilin Should Learn From Edict

### 7.1 Directly adoptable ideas

- explicit task/project pipeline visibility
- event-driven orchestration with recovery-aware workers
- operator-facing intervention controls
- better live state and activity surfaces
- stronger admin/debug/health tooling

### 7.2 Ideas to adapt carefully

- review gates
  - useful, but should map to OpenQilin's governance roles rather than historical departments
- dashboard model/config management
  - useful, but should be governed and auditable
- skill and session observability
  - useful, but should stay secondary to project execution and operator clarity

### 7.3 Ideas to reject

- metaphor-first product identity
  - OpenQilin should not depend on a historical bureaucracy metaphor to explain itself
- platform-on-platform dependency shape as the default
  - too much setup pain and coupling
- generalized multi-agent theater over focused operator value
  - bad fit for the solopreneur thesis

## 8. Implications for MVP-v2

Edict reinforces several MVP-v2 priorities already emerging for OpenQilin:

- Discord-first is still a good MVP boundary.
- Project-space routing is better than identity sprawl.
- JSON-shaped daily UX should be replaced by hybrid free-text plus compact commands.
- Setup pain must be treated as a product problem, not documentation debt.
- Observability and intervention need to become first-class product surfaces.
- Per-agent LLM profiles and runtime bindings will matter if roles are meant to feel real.

Edict also sharpens two warnings:

- If OpenQilin builds too much metaphor and too little operator value, it will become a showcase instead of a tool.
- If OpenQilin layers on top of another agent platform too deeply, it risks inheriting complexity instead of eliminating it.

## 9. Bottom Line

Edict is a better directional reference for OpenQilin than OpenClaw is in terms of organizational form and orchestration posture.

But OpenQilin should not become "Edict for Discord."

The stronger path is:
- keep OpenQilin's solopreneur thesis
- keep governance and project-centered execution as the core
- learn from Edict's observability, orchestration, and intervention design
- avoid Edict's dependency layering and metaphor-heavy product framing

In short:
- OpenClaw shows how to build a broad assistant platform.
- Edict shows how to impose visible orchestration on top of such a platform.
- OpenQilin should aim for a third thing: a focused, governed operating system for one serious operator.
