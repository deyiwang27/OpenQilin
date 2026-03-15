# ZeroClaw Spike Report

Date: `2026-03-15`
Status: `complete`
Stage: `post-kickoff`

---

## 1. Purpose

- Investigate the ZeroClaw repository as a potential reference for OpenQilin v2.
- Extract practical lessons without collapsing OpenQilin into a copy of ZeroClaw.
- Produce an adopt / adapt / consider / reject decision for each finding.
- Determine whether any finding belongs in MVP-v2 scope or should be deferred.

---

## 2. Scope and Sources

Primary ZeroClaw sources reviewed:

- Repository root: https://github.com/zeroclaw-labs/zeroclaw/tree/master
- `src/agent/loop_.rs` — agent turn loop
- `src/agent/classifier.rs` — model cost routing classifier
- `src/agent/dispatcher.rs` — tool call dispatcher (native vs. XML)
- `src/memory/consolidation.rs` — two-phase LLM memory consolidation
- `src/memory/vector.rs` — hybrid vector + BM25 memory fusion
- `src/memory/hygiene.rs` — background memory cleanup with cadence guard
- `src/memory/snapshot.rs` — git-backed Markdown snapshot of core memory
- `src/memory/response_cache.rs` — SHA-256 keyed response cache with TTL + LRU eviction
- `src/cost/tracker.rs` — per-model cost tracking with soft-warn and hard-block thresholds
- `src/approval/mod.rs` — autonomy level and session-scoped approval system
- `src/hooks/runner.rs` — priority-based hook pipeline with short-circuit cancel
- `src/daemon/mod.rs` — supervisor with exponential backoff and health snapshot
- `src/channels/discord.rs` — raw Discord Gateway WebSocket implementation
- `src/channels/session_store.rs` — append-only JSONL session store

Point-in-time observation:

- branch: `master`
- review date: `2026-03-15`

---

## 3. Executive Summary

ZeroClaw is a single-binary, Rust-based personal assistant runtime with the design goal of "zero overhead, zero compromise" — sub-10ms cold starts, <5MB RAM, SQLite primary storage, deployable on embedded hardware. It targets individual developers who want a self-hosted AI agent with no cloud dependencies.

Its architecture is a Tokio-based async supervisor that spawns: an HTTP gateway, one or more messaging channel listeners (Discord, Telegram, Slack, and 20+ others), a cron scheduler, and a heartbeat engine. The agent loop is a single-LLM tool-calling loop. There is no multi-agent graph, no policy engine, no versioned governance rules, and no concept of governed role separation.

**Verdict:** ZeroClaw and OpenQilin are solving different problems. ZeroClaw optimises for minimal footprint and easy personal deployment. OpenQilin optimises for governed, auditable, multi-agent AI operation for a solopreneur *operator* with budget attribution, OPA-enforced policies, and constitutional authority separation. The comparison is instructive precisely because the design constraints diverge so clearly.

Three specific implementation patterns have direct value for OpenQilin. None belong in MVP-v2 scope. All others are either already handled better by OpenQilin's existing design or are appropriate for future phases.

---

## 4. Findings

### 4.1 Rule-Based Model Classifier for Cost Routing

**Source:** `src/agent/classifier.rs`, `src/agent/agent.rs`

ZeroClaw's `classify()` function matches user messages against priority-ordered rules (keywords + regex with length constraints) and routes to cheaper/faster models for qualifying queries. The routing hint (`hint:fast`, `hint:complex`) is prepended to the model identifier before the LLM call. Cheap queries (status checks, quick lookups) go to Haiku; complex ones go to Sonnet or Opus.

**Why it matters for OpenQilin:** A solopreneur operator on a fixed LLM budget benefits directly from not spending Sonnet tokens on simple queries. OpenQilin's LLM Gateway currently applies no query-level routing.

**Decision:** Adopt — implement in OpenQilin's LLM Gateway as a budget optimisation layer after M14 (token cost model and budget ledger are live). Cannot be validated without real cost visibility.

---

### 4.2 Two-Phase LLM Memory Consolidation

**Source:** `src/memory/consolidation.rs`

After each conversation turn, a second LLM call extracts:

1. A timestamped `history_entry` summary → stored as a daily episodic record.
2. A `memory_update` with novel long-term facts → stored in Core memory (or `null` if nothing new).

The prompt enforces exactly two JSON fields. A markdown-wrapped fallback parser handles malformed output. Input text is truncated at 4,000 chars before the consolidation call.

This cleanly separates episodic memory (daily log) from semantic memory (long-term facts), avoiding the conflation that makes most retrieval implementations hard to audit.

**Why it matters for OpenQilin:** OpenQilin's retrieval runtime will need a consolidation pipeline. This is a concrete, working reference implementation.

**Decision:** Adopt — use as a reference implementation for OpenQilin's retrieval runtime consolidation pipeline after M15 (conversation persistence is stable and usage patterns are understood).

---

### 4.3 Memory Hygiene with Cadence Guard

**Source:** `src/memory/hygiene.rs`

The hygiene module runs at most every 12 hours (cadence tracked in a JSON state file), performs five cleanup tasks including archiving old session files, purging archived memories past retention, and pruning stale rows with non-blocking reads. The "best-effort, non-critical" failure pattern — failures are logged and ignored rather than propagated — is appropriate for background maintenance.

**Why it matters for OpenQilin:** OpenQilin's PostgreSQL conversation table will accumulate rows without bounds. A hygiene job with a cadence guard and non-critical failure handling is the right operational pattern.

**Decision:** Adopt — implement for OpenQilin's PostgreSQL conversation table after M14, once the Grafana dashboard makes row growth observable and retention requirements are clear.

---

### 4.4 Hybrid Memory Merge — Vector + BM25 Fusion

**Source:** `src/memory/vector.rs`

ZeroClaw's `hybrid_merge()` normalises BM25 scores against the max in the result set and computes:

```
final_score = vector_weight * vector_score + keyword_weight * keyword_score
```

Results are deduplicated by ID and top-N trimmed. This is a dependency-free, portable formula.

**Decision:** Adapt — validate that OpenQilin's retrieval runtime implements equivalent hybrid fusion; use this as a reference if not.

---

### 4.5 Cost Tracker with Soft-Warn and Hard-Block Thresholds

**Source:** `src/cost/tracker.rs`

ZeroClaw tracks per-model token usage in an append-only JSONL file and enforces both a configurable warn threshold and a hard daily/monthly block. Warnings fire *before* blocking — the operator sees the approaching limit before being stopped.

**Decision:** Adapt — verify that OpenQilin's M14 budget runtime implements both soft-warn and hard-block thresholds, not just hard-block. Add warn thresholds if missing.

---

### 4.6 Hook Pipeline with Priority and Short-Circuit Cancel

**Source:** `src/hooks/runner.rs`

The `HookRunner` distinguishes fire-and-forget hooks (concurrent, no return) from sequential modifying hooks (priority-ordered, piped output, cancellable via `HookResult::Cancel`). Panic resilience uses `AssertUnwindSafe`.

**Decision:** Consider — the short-circuit Cancel pattern is worth incorporating into OpenQilin's pre-execution policy check pipeline if we add plugin/hook extensibility in post-MVP phases.

---

### 4.7 Response Cache with SHA-256 Keying, TTL, and LRU Eviction

**Source:** `src/memory/response_cache.rs`

Avoids re-spending tokens on identical queries within a TTL window. Cache key: `(model, system_prompt_hash, user_input_hash)`.

**Decision:** Consider — worth adding to OpenQilin's LLM Gateway if LLM costs become a dominant operator concern. Implement after the model classifier (4.1) is in place.

---

### 4.8 Per-Component Health Snapshot File

**Source:** `src/daemon/mod.rs`

Every 5 seconds, `daemon_state.json` is written with component health, restart counts, and error messages. Useful for operators who want a quick `cat daemon_state.json` without opening Grafana.

**Decision:** Consider — supplementary to Prometheus metrics for solopreneur operators. Low implementation cost. Revisit during M15 (runtime polish / doctor CLI).

---

### 4.9 Git-Backed Markdown Snapshot of Core Memory

**Source:** `src/memory/snapshot.rs`

Core memories are exported to a version-controlled Markdown file after each write. On restart with a missing database, the system rehydrates from the snapshot. Useful for operator auditability of agent "soul" state.

**Decision:** Consider — useful as an optional export mechanism for OpenQilin's constitution/memory layer, not as a primary persistence strategy. Revisit in post-MVP phases.

---

### 4.10 Raw Discord Gateway WebSocket Implementation

**Source:** `src/channels/discord.rs`

ZeroClaw implements the Discord Gateway protocol directly (opcodes 1/2/7/9/10, heartbeat, sequence tracking, resume on reconnect) without a Discord library. Instructive for understanding which lifecycle events matter.

**Decision:** Reject for adoption — OpenQilin's Python Discord library abstraction is the right trade-off. Use only as a protocol reference.

---

### 4.11 Approval via In-Memory Name Lists

**Source:** `src/approval/mod.rs`

Three autonomy levels plus `auto_approve`/`always_ask`/session-scoped lists. Not versioned, not auditable, not expressive.

**Decision:** Reject — OPA Rego policies already handle this correctly with versioning, audit trails, and a policy language.

---

### 4.12 Single-Agent Loop Architecture

**Source:** `src/agent/loop_.rs`

One LLM, one agent, one turn. No delegation, no role separation, no graph.

**Decision:** Reject — OpenQilin's LangGraph graph with typed state transitions and role-separated agents (Secretary, CSO, DL) cannot be approximated by a single-agent loop.

---

### 4.13 SQLite as Primary Persistence

**Decision:** Reject — OpenQilin's PostgreSQL-first approach with Alembic-managed schema evolution is correct for concurrent multi-agent operation and audit requirements.

---

## 5. What OpenQilin Already Does Better

| Area | ZeroClaw | OpenQilin |
|---|---|---|
| Policy enforcement | Hardcoded autonomy levels and name lists | Versioned OPA Rego policies with audit trail |
| Multi-agent orchestration | Single-agent loop only | LangGraph graph with typed nodes, edges, and role-separated agents |
| Persistence | SQLite primary | PostgreSQL with Alembic migrations |
| Observability | Local JSON health file | Grafana + Prometheus + structured audit log |
| Budget governance | JSONL file, per-session only | PostgreSQL ledger with reservation and cost attribution across agent roles |
| Discord authority model | Allowlist per channel | Role-bot registry with OPA-enforced authority separation |
| Constitutional governance | None | Constitution layer with enforceable Rego policies |
| Deployment separation | Single Rust binary monolith | Componentised Python services with explicit contracts |

---

## 6. Decision Table

| # | Finding | Decision | Trigger |
|---|---|---|---|
| 4.1 | Model classifier for cost routing | **Adopt** | After M14 (budget ledger + cost model live) |
| 4.2 | Two-phase LLM memory consolidation | **Adopt** | After M15 (conversation persistence stable) |
| 4.3 | Memory hygiene with cadence guard | **Adopt** | After M14 (row growth observable in Grafana) |
| 4.4 | Hybrid vector + BM25 fusion | **Adapt** | Validate retrieval runtime; apply if missing |
| 4.5 | Soft-warn + hard-block budget thresholds | **Adapt** | During M14-WP3 (budget obligation enforcement) |
| 4.6 | Hook pipeline with Cancel | **Consider** | Post-MVP plugin/hook extensibility |
| 4.7 | Response cache with TTL + LRU | **Consider** | If LLM costs dominate post-MVP |
| 4.8 | Per-component health snapshot file | **Consider** | During or after M15 (doctor CLI) |
| 4.9 | Git-backed core memory snapshot | **Consider** | Post-MVP memory/constitution phase |
| 4.10 | Raw Discord WebSocket | **Reject** | Protocol reference only |
| 4.11 | Approval via name lists | **Reject** | OPA already handles this correctly |
| 4.12 | Single-agent loop architecture | **Reject** | Incompatible with multi-agent design |
| 4.13 | SQLite as primary persistence | **Reject** | PostgreSQL + Alembic is strictly better |

---

## 7. MVP-v2 Impact Assessment

**None of the three adopt findings belong in MVP-v2 scope.**

- **Model classifier (4.1)** requires a live token cost model and budget ledger to validate against. M14 must ship first.
- **Memory consolidation (4.2)** presupposes stable conversation persistence. M15-WP2 must ship first.
- **Memory hygiene (4.3)** presupposes observable row growth. The M14 Grafana dashboard must be live first.

MVP-v2 (M11–M16) is focused on closing the gap between what OpenQilin claims in spec and what it actually enforces at runtime: real OPA, real PostgreSQL, real Redis, LangGraph active, security bugs fixed, agents properly activated. The ZeroClaw findings are optimisation and polish layers that presuppose a working, stable foundation.

**Recommendation:** record the three adopt findings as deferred post-MVP backlog items. Revisit after M16 when the runtime is stable and real usage data is available.

---

## 8. Related Documents

- `04-research/OpenClawSpikeReport-v1.md` — OpenClaw comparison spike
- `04-research/OpenClawReferenceLearningReport-v1.md` — OpenClaw adopt/adapt/reject learnings
- `04-research/ExternalReferenceLandscapeSpike-v1.md` — external reference landscape scan
- `05-milestones/M14-WorkPackages-v1.md` — M14 budget persistence and token cost model
- `05-milestones/M15-WorkPackages-v1.md` — M15 conversation persistence and runtime polish
