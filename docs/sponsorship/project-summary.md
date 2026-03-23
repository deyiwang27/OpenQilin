# OpenQilin — Project Summary

**A governed AI operating system for the solopreneur.**

---

## What is OpenQilin?

OpenQilin turns one capable person into a coordinated AI-augmented team. It does this by treating authority, policy, budget, and audit not as documentation but as runtime constraints — every agent action is authorised by a live policy engine, recorded immutably, and cost-tracked before it happens.

**Who it is for:** Solopreneur operators who need to delegate complex, ongoing work to AI agents with real governance and cost control — not just a chatbot.

---

## What MVP-v2 delivers

MVP-v2 is complete as of March 2026. The system is running, tested, and documented.

**9 active institutional agent roles:** Secretary (interaction), Administrator and Auditor (governance), CSO / CEO / CWO (executive), Domain Leader and Project Manager (operations), Specialist (execution).

**Full governance stack:**
- OPA policy runtime with versioned Rego bundle — every action authorised before execution
- LangGraph orchestration pipeline — policy → obligation → budget → dispatch
- PostgreSQL persistence — task state, budget ledger, conversation history, audit trail, project artifacts
- Real token cost model with per-project budget enforcement
- Grafana operator dashboard — 8 panels covering project health, budget, system health, and governance events
- Diagnostics CLI (`oq_doctor`) — checks all infrastructure connections at startup

**Interaction surface:** Discord (natural language + `/oq` command grammar)

**Test coverage:** 785 unit and component tests passing. Fail-closed by default throughout.

---

## Current traction

- Public GitHub repository: [github.com/deyiwang89/OpenQilin](https://github.com/deyiwang27/OpenQilin)
- MVP-v2 fully implemented across 6 milestones (M11–M16), 44 work packages, 120+ PRs
- Open-source, Apache 2.0 licensed
- Contributor entry path published (CONTRIBUTING.md, good first issues)

---

## What support would unlock

| Resource | How it would be used |
|---|---|
| LLM API credits (Gemini / Anthropic) | Run governed agent workflows in development and integration testing without per-call billing pressure |
| Cloud compute credits (AWS / GCP) | Host a live demo environment for contributors and early users |
| Observability credits (Grafana Cloud / similar) | Run the Grafana + OTel stack without self-hosting overhead during early public use |

OpenQilin does not require large-scale compute. The primary cost driver is LLM inference during development and demo operations.

---

## Contact

**Project lead:** Deyi Wang (deyiwang27)
**GitHub:** [github.com/deyiwang27/OpenQilin](https://github.com/deyiwang27/OpenQilin)
**Email:** *(add contact email when available — see M17-WP5)*

---

*Apache 2.0 open-source. Built for solopreneurs. Governed end-to-end.*
