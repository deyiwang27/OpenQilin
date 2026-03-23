# OpenQilin Roadmap

This roadmap summarises what OpenQilin has delivered, where it is heading, and what it will deliberately not become.

Items here are **themes and goals**, not commitments or deadlines. The project is early-stage and priorities shift as real usage reveals what matters most.

---

## Completed — MVP-v1

MVP-v1 established the project's institutional role model and governance concept:

- Defined the constitutional role hierarchy: `owner`, `administrator`, `auditor`, `ceo`, `cwo`, `project_manager`, `domain_leader`, `specialist`
- Established Discord as the operator interaction surface
- Introduced the governed task lifecycle model and project-space concept
- Scaffolded OPA-based policy enforcement (declared but not yet wired at runtime)
- Produced the initial spec, governance architecture, and authority model

MVP-v1 proved the governance identity of the project. The runtime was largely in-memory and not production-ready.

---

## Completed — MVP-v2

MVP-v2 made the governance model real at every layer. All major infrastructure, orchestration, and agent components are now wired and tested.

**Governance and policy:**
- Live OPA policy runtime with versioned Rego bundle loaded from source tree
- Fail-closed orchestration: every agent action authorised by OPA before execution
- Constitutional obligation enforcement (budget, approval, retention)
- Immutable audit event trail persisted in PostgreSQL

**Orchestration:**
- LangGraph pipeline: policy evaluation → obligation check → budget approval → agent dispatch
- Loop controls: per-task hop caps and PM→Specialist pair caps with breach metrics
- Idempotent task admission with Redis deduplication

**Agent activation (all 9 roles):**
- **Secretary** — intent classification, free-text routing, project-space dispatch; advisory-only
- **CSO** (Chief Strategy Officer) — portfolio governance advisor; GATE-006 record writes
- **Domain Leader** — virtual agent; project-space coordinator and escalation point
- **Project Manager** — task planning, status reports, Specialist dispatch
- **CEO** — directive authority, GATE-003/004/005, co-approval enforcement
- **CWO** (Chief Workflow Officer) — command authority, project charter writes
- **Auditor** — compliance monitoring, ESC-005/006 escalation, behavioural violation path
- **Administrator** — agent lifecycle, document policy enforcement, retention enforcement
- **Specialist** — task execution and task execution result writes

**Infrastructure:**
- PostgreSQL persistence: task state, budget ledger (15 Alembic migrations), conversation history, project artifacts, project-space bindings
- File-backed artifact storage with content hash verification
- OpenTelemetry tracing, metrics, and structured log export
- Grafana operator dashboard: 8 panels covering project health, budget utilisation, system health, LLM activity, and governance events
- Grafana alerting with Discord webhook integration
- `oq_doctor` diagnostics CLI: checks all infrastructure connections at startup and on demand
- Classification result cache (60-second TTL) and `llm_calls_total` Prometheus metrics

---

## Next — Post-MVP-v2 Themes

These are directions the project is considering after MVP-v2. None have delivery dates.

**Full sandbox isolation**
Specialist task execution has scaffolding for seccomp/BPF process isolation but no enforcement. Full BPF-based sandbox with verified profiles is the next major safety investment.

**Broader chat adapter support**
Discord is the only interaction surface today. Adding Slack and other adapters would broaden the operator audience without changing the governance model.

**Operator console**
A lightweight web UI for project and agent management — viewing active projects, reviewing blocked tasks, and approving governance gates — without needing Discord.

**Multi-bot Discord configuration guide**
First-class support for per-role Discord bot tokens, so each agent role appears as a distinct Discord user. Currently supported but requires manual configuration.

**Governance template library**
Starter policy presets and project-space templates for common solopreneur workflows (content production, software development, research).

**Community-maintained integrations**
An extension model that lets contributors add LLM provider adapters, project tooling integrations, and dashboard widgets without modifying core governance logic.

**PM→DL pair-hop enforcement**
The PM→Domain Leader escalation path currently skips pair-cap checking (the escalation is synchronous within the LLM dispatch path). Wiring full `LoopState` propagation through this path is a near-term polish item.

---

## Non-Goals

These are things OpenQilin deliberately will not try to become:

- **Not a general multi-agent AI framework.** OpenQilin is purpose-built for the solopreneur operator model. It is not designed for arbitrary agentic workflows or for teams building custom agent platforms on top of it.
- **Not a multi-user SaaS product.** The governance model assumes a single owner-operator. Multi-tenancy, user accounts, and subscription billing are out of scope.
- **Not a code generation or IDE tool.** OpenQilin delegates work and coordinates execution; it does not write code or integrate with editors.
- **Not a replacement for human project management software.** OpenQilin coordinates AI-delegated work, not human team calendars, sprint boards, or HR processes.

---

## Contributing

If any of these themes interest you, see [CONTRIBUTING.md](CONTRIBUTING.md) for how to get involved.
