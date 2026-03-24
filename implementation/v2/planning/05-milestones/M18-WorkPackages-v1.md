# M18 Work Packages — Conversational UX Completion and Public Launch

Milestone: `M18`
Status: `planned`
Entry gate: M17 complete (open-source readiness done; conversation memory foundation live)
Supporting docs: `design/v2/architecture/ConversationMemoryDesign-v1.md`, `03-community/OpenSourceCommunityStrategy-v1.md`, `03-community/FundingAndSponsorshipStrategy-v1.md`

---

## Milestone Goal

Make every institutional agent a first-class conversational participant, then launch OpenQilin publicly with a live demo and web presence. After M17, Secretary is the only agent with an LLM-backed conversational mode. M18 gives each agent its own role-appropriate advisory voice, wires the `@everyone` broadcast, and ends with the demo recording and website that were deferred from M17 so they reflect the full, feature-complete product.

---

## WP M18-01 — Conversational Advisory Mode for Institutional Agents

**Goal:** Give each institutional bot (CEO, CWO, Auditor, Administrator, CSO, Project Manager) its own LLM-backed conversational response when @mentioned with free text in Discord — the same pattern as Secretary's `_generate_advisory`, but from each agent's own role identity and perspective. All conversational responses are advisory only: no state mutations, no task dispatch, no identity verification required.

**Design ref:** `src/openqilin/agents/secretary/agent.py` (`_generate_advisory` pattern to replicate); `src/openqilin/control_plane/routers/discord_ingress.py` (secretary advisory bypass to generalize); `src/openqilin/apps/discord_bot_worker.py` (canned intro gates to replace)

### Background

After M17-WP9 and the post-merge routing fixes, when a non-Secretary bot is @mentioned with free text, `discord_bot_worker.py` posts a canned "Hello! I'm the X agent" intro and returns — the message is never forwarded to the control plane. This was a placeholder fix. M18-WP1 replaces the placeholder with real LLM-backed advisory responses.

Similarly, non-Secretary DM free-text is intercepted in the bot worker with a usage hint. M18-WP1 upgrades this to a real advisory response.

### Spec Gaps Carried Forward from M17 Post-Merge Review

**Gap 1 — Secretary `ADVISORY_SYSTEM_PROMPT` routes new-project discussions to PM (wrong)**

The current Secretary prompt (`src/openqilin/agents/secretary/prompts.py`) says:
> "For project work: ask via `/oq ask project_manager <project> <question>`"

This is only correct for work on an **existing approved project**. When an owner discusses starting a **new project**, the correct process per `spec/governance/architecture/DecisionReviewGates.md` is:

```
CWO drafts project charter
  → GATE-001: CSO strategic review (Aligned / Needs Revision / Strategic Conflict)
  → GATE-003: CEO + CWO review
  → GATE-004: Owner + CEO approval → project state = approved
  → GATE-005: CWO workforce initialization command → project state = active
```

PM is NOT a participant until the project reaches `approved` or `active` state.

**Fix (task 0 below):** Update `ADVISORY_SYSTEM_PROMPT` to distinguish project creation (route to CWO; explain CSO → CEO → CWO gate flow) from existing project work (route to PM).

**Gap 2 — CEO, CWO, CSO conversational prompts must reflect the gate flow**

Each agent's `_CONVERSATIONAL_SYSTEM_PROMPT` must accurately describe GATE-001 through GATE-005:
- **CEO:** receives proposals after CSO strategic review (GATE-003); co-reviews with CWO and approves at GATE-004
- **CWO:** drafts the project charter and submits; leads workforce initialization at GATE-005 after approval
- **CSO:** performs the first mandatory strategic review (GATE-001) before any CEO/CWO review; outcomes: `Aligned`, `Needs Revision`, `Strategic Conflict`

**Gap A — `discord_bot_worker.py` canned intro must be replaced**

The group-channel @mention gate (commit #191) posts a canned intro and returns without forwarding to the control plane. This prevents the M18 advisory bypass from ever being reached. The canned intro block must be replaced with control-plane forwarding identical to the Secretary path.

**Gap B — DM gate in `discord_bot_worker.py` must be relaxed**

Commit #191 also added a gate that intercepts non-Secretary DM free-text and returns a usage hint. The M18 done criteria require DMs to trigger advisory responses. This gate must be removed or relaxed so the message is forwarded to the control plane.

**Gap C — `conversation_store` None-safety**

`conversation_store` is `None` when `runtime_persistence_enabled=False`. All six `handle_free_text()` implementations must guard with `if self._conversation_store:` before list/append calls — same pattern as Secretary.

**Gap D — `llm_calls_total` metric for advisory calls**

CEO, CWO, CSO, and PM already have `llm_gateway` injected but do not emit `llm_calls_total`. Auditor and Administrator will gain `llm_gateway` in this WP. All six agents' `handle_free_text()` implementations must call `self._metric_recorder.record_llm_call(...)` if a metric recorder is available. Wire `metric_recorder` into Auditor and Administrator in `build_runtime_services()`.

---

### Tasks

- [x] **[Gap 1 fix]** Update `ADVISORY_SYSTEM_PROMPT` in `src/openqilin/agents/secretary/prompts.py`: distinguish new-project initiation (route to CWO; explain CSO → CEO → CWO gate sequence) from existing-project work (route to PM)
- [x] **[Gap A fix]** In `discord_bot_worker.py`: replace the canned "Hello! I'm the X agent" intro-and-return block with control-plane forwarding (call `process_event()` as Secretary does) for non-Secretary @mention in group channels
- [x] **[Gap B fix]** In `discord_bot_worker.py`: remove or relax the DM gate that intercepts non-Secretary DM free-text; forward to control plane so advisory response is generated
- [x] Add `FreeTextAdvisoryRequest` and `FreeTextAdvisoryResponse` dataclasses to new module `src/openqilin/agents/shared/free_text_advisory.py`
- [x] Add `handle_free_text()` method and `_CONVERSATIONAL_SYSTEM_PROMPT` to `CeoAgent`; inject `conversation_store` and `metric_recorder` into constructor (Gap 2: prompt must describe GATE-003/GATE-004)
- [x] Add `handle_free_text()` method and `_CONVERSATIONAL_SYSTEM_PROMPT` to `CwoAgent`; inject `conversation_store` and `metric_recorder` into constructor (Gap 2: prompt must describe GATE-005 and charter authorship)
- [x] Add `handle_free_text()` method and `_CONVERSATIONAL_SYSTEM_PROMPT` to `AuditorAgent`; inject `llm_gateway`, `conversation_store`, and `metric_recorder` into constructor
- [x] Add `handle_free_text()` method and `_CONVERSATIONAL_SYSTEM_PROMPT` to `AdministratorAgent`; inject `llm_gateway`, `conversation_store`, and `metric_recorder` into constructor
- [x] Add `handle_free_text()` method and `_CONVERSATIONAL_SYSTEM_PROMPT` to `CSOAgent`; inject `conversation_store` and `metric_recorder` into constructor (Gap 2: prompt must describe GATE-001 and its three outcomes)
- [x] Add `handle_free_text()` method and `_CONVERSATIONAL_SYSTEM_PROMPT` to `ProjectManagerAgent`; inject `conversation_store` into constructor
- [x] **[Gap C]** All six `handle_free_text()` implementations guard `conversation_store` usage with `if self._conversation_store:` — must not fail when persistence is disabled
- [x] **[Gap D]** Wire `metric_recorder` into Auditor and Administrator in `build_runtime_services()`; all six `handle_free_text()` calls emit `llm_calls_total` via `metric_recorder` if available
- [x] Generalize the secretary advisory bypass in `discord_ingress.py` to a six-agent routing block: gate on `payload.bot_role`, build `FreeTextAdvisoryRequest`, dispatch to the matching agent's `handle_free_text()`, return advisory response — wrap in broad `try/except` so advisory failure never 500s
- [x] Wire `conversation_store` into CEO, CWO, CSO, PM in `build_runtime_services()`; wire `llm_gateway`, `conversation_store`, and `metric_recorder` into Auditor and Administrator
- [x] Create `src/openqilin/agents/auditor/prompts.py` and `src/openqilin/agents/administrator/prompts.py` for the new conversational system prompts
- [x] Unit tests for each agent's `handle_free_text()`: happy path, fallback path, store absent, store present (6 × 4 = 24 test cases minimum)
- [x] Static checks pass: `ruff`, `mypy`, InMemory grep gate, `pytest tests/unit tests/component`

### Agent System Prompts (spec)

Each agent receives its own `_CONVERSATIONAL_SYSTEM_PROMPT`. Key constraints for all:
- Identify as the agent role (NOT Secretary)
- Advisory only — explicitly state no mutations or task dispatch in this mode
- List role responsibilities in 3-5 bullet points
- Provide example `/oq ask <role> <topic>` commands
- Max output: 3-5 sentences

| Agent | Role identity | Scope | Gate-flow role (Gap 2) |
|---|---|---|---|
| CEO | Executive decision authority | Strategic directives, proposal approval, co-approval with CWO, executive escalation | **GATE-003** co-review with CWO; **GATE-004** approval with owner; project state → `approved` |
| CWO | Chief Workforce Officer | Workforce initialization, Specialist activation, role binding, project charter authorship | **Drafts** project charter and submits proposal; **GATE-005** workforce initialization command after approval → `active` |
| Auditor | Governance oversight | Violation recording, ESC-005/006 escalation, document compliance monitoring | — |
| Administrator | Infrastructure and policy enforcement | Document policy, retention enforcement, agent quarantine, hash integrity | — |
| CSO | Portfolio strategy advisor | Strategic alignment review, cross-project conflicts, opportunity cost, escalation recommendations | **GATE-001** first mandatory strategic review; outcomes: `Aligned` → advances; `Needs Revision` → loops; `Strategic Conflict` → blocks after 3 cycles |
| PM | Project operational authority | Status reports, task assignment, Specialist dispatch, DL escalation, controlled document authorship | Only participates after project reaches `approved`/`active` — **not involved in proposal phase** |

### Control-plane routing (spec)

In `discord_ingress.py`, after the `resolved_target == "secretary"` block, add:

```python
_ADVISORY_AGENT_ROLES: frozenset[str] = frozenset({
    "ceo", "cwo", "auditor", "administrator", "cso", "project_manager"
})

if payload.bot_role in _ADVISORY_AGENT_ROLES:
    # validate_connector_auth (same as secretary block)
    # build FreeTextAdvisoryRequest from payload + intent + grammar_context
    # dispatch to the matching agent's handle_free_text()
    # return OwnerCommandResponse with llm_execution={"advisory_response": resp.advisory_text}
    # wrap in broad try/except — advisory failure must not 500
```

### Conversation history (spec)

All `handle_free_text()` implementations use scope `f"guild::{guild_id}::channel::{channel_id}"` (M17-WP8 unified key). `list_turns()` before the LLM call; `append_turns()` after. The `agent_id` written is the agent's role string.

### Outputs

- `src/openqilin/agents/shared/free_text_advisory.py` — shared request/response dataclasses
- `_CONVERSATIONAL_SYSTEM_PROMPT` + `handle_free_text()` on each of: CeoAgent, CwoAgent, AuditorAgent, AdministratorAgent, CSOAgent, ProjectManagerAgent
- `src/openqilin/agents/auditor/prompts.py` and `src/openqilin/agents/administrator/prompts.py`
- Updated `discord_bot_worker.py`: group-channel and DM gates forward to control plane
- Updated `discord_ingress.py`: six-agent advisory bypass
- Updated `build_runtime_services()`: all six agents wired with `conversation_store`; Auditor and Administrator also get `llm_gateway` and `metric_recorder`

### Done criteria

- [ ] @mentioning any institutional bot in a Discord group channel with free text triggers an LLM-generated, role-appropriate response posted by that agent's bot — not a canned stub, not Secretary
- [ ] @mentioning in a DM also triggers an advisory response
- [ ] Each agent's response correctly identifies itself (not Secretary) and gives role-specific guidance
- [ ] Conversation history is persisted and reused across turns (multi-turn test per agent)
- [ ] No `handle_free_text()` dispatches tasks or mutates state
- [ ] `/oq ask <agent>` and all explicit commands continue working (no regression)
- [ ] `ruff`, `mypy`, InMemory gate, `pytest tests/unit tests/component` all pass

---

## WP M18-02 — @everyone Broadcast

**Goal:** When `@everyone` is used in a Discord channel, all 7 agents (Secretary + the six institutional bots) respond simultaneously, each with their own role-appropriate introduction via `handle_free_text()`.

**Design ref:** M18-WP1 `handle_free_text()` implementations (prerequisite)

**Entry gate:** M18-WP1 done (all six agents must have `handle_free_text()` before broadcast can call them)

### Tasks

- [x] Add `is_everyone_mention: bool` field to `DiscordInboundEvent` (default `False`)
- [x] In `discord_bot_worker.py`: detect `message.mention_everyone`; set `is_everyone_mention=True` on the event; all 7 bot processes forward to the control plane (do not early-return)
- [x] In `discord_ingress.py`: when `is_everyone_mention=True`, route this bot's request directly to its own advisory handler; return only that bot's advisory response
- [x] Ensure duplicate suppression: if `@everyone` triggers all 7 bots, each bot's control-plane call only posts its own agent's response (not all 7)
- [x] Unit tests: bot-worker gate, ingress fast-path, and payload passthrough coverage for `@everyone`

### Outputs

- `is_everyone_mention` field on `DiscordInboundEvent`
- Broadcast routing in `discord_ingress.py`
- Bot-worker detection logic

### Done criteria

- [x] `@everyone` in any channel causes all 7 agent bots to post their own role intro
- [x] Each bot posts only its own response, not other agents'
- [x] No regression on single-agent @mention or explicit `/oq` commands

---

## WP M18-03 — Demo Assets

> Moved from M17-WP3. Demo is recorded against the feature-complete product (including M18-WP1 conversational advisory mode and M18-WP2 @everyone broadcast).

**Goal:** Create a reusable, convincing end-to-end demo that showcases the solopreneur use case including all conversational agents. Demo should work for outreach, README, and presentations.

**Design ref:** `03-community/OpenSourceCommunityStrategy-v1.md §4.2`

**Entry gate:** M18-WP1 done (conversational advisory mode must be live before demo is recorded)

### Tasks

- [ ] Write demo script: one concrete solopreneur workflow end-to-end:
  1. Owner @mentions `@everyone` — all 7 agents introduce themselves
  2. Owner discusses starting a new project with @secretary — Secretary routes to CWO and explains gate flow
  3. Owner creates a project via Discord (`/oq create project "Website Redesign"`)
  4. PM responds in project space; DL escalation visible when needed
  5. Budget allocation visible in Grafana Budget panel
  6. CSO governance gate visible on a policy-sensitive action
  7. Owner views blocked task and approves in Discord
  8. Audit trail visible in Grafana Audit panel
- [ ] Record demo as screen recording (or animated GIF for README) — narrated or captioned
- [ ] Write companion `docs/demo/` folder with step-by-step text walkthrough usable in README and outreach
- [ ] Confirm demo runs on a clean `docker compose up` without manual setup beyond `.env` config

### Outputs

- Demo script and screen recording / GIF
- `docs/demo/` walkthrough text
- Demo runnable from clean checkout

### Done criteria

- [ ] Demo showcases conversational advisory mode, governance, project execution, budget visibility, and audit trail
- [ ] Demo runs on clean checkout without prior context
- [ ] Demo asset usable in GitHub README, social media post, and sponsorship deck

---

## WP M18-04 — Website and Public Presence

> Moved from M17-WP5. Website launch coincides with the fully complete product and recorded demo.

**Goal:** Establish a minimal public web presence with a domain, landing page, and contact email. Required for sponsorship applications and contributor discovery.

**Design ref:** `03-community/FundingAndSponsorshipStrategy-v1.md §4.2`

**Entry gate:** M18-WP3 done (demo link must exist before website is published)

### Tasks

- [ ] Acquire or confirm domain (e.g. `openqilin.dev` or equivalent)
- [ ] Build minimal landing page (single-page; no CMS required):
  - Product one-liner and thesis
  - Link to GitHub repo
  - Link to demo / quick start
  - Contact email (`hello@<domain>` or equivalent)
  - "Star on GitHub" CTA
- [ ] Set up `hello@<domain>` or equivalent contact email
- [ ] Add website link to GitHub repo description and `README.md`

### Outputs

- Public domain with live landing page
- Public contact email operational

### Done criteria

- [ ] Landing page live at public domain
- [ ] Contact email receives test message
- [ ] Website URL in GitHub repo description and `README.md`

---

## M18 Exit Criteria

- [ ] All four WPs above are marked done
- [ ] Every institutional agent responds to @mentions with an LLM-generated conversational reply from its own identity
- [ ] `@everyone` triggers simultaneous introductions from all 7 agents
- [ ] Demo recorded against the complete product and linked from README
- [ ] Website and contact email live at public domain
- [ ] Conversation memory persisted per channel across all agents
- [ ] No regression in existing task-dispatch or governance flows

## References

- `src/openqilin/agents/secretary/agent.py` — advisory pattern reference
- `design/v2/architecture/ConversationMemoryDesign-v1.md` — conversation store design
- `03-community/OpenSourceCommunityStrategy-v1.md` — community and demo strategy
- `03-community/FundingAndSponsorshipStrategy-v1.md` — website and sponsorship strategy
- `implementation/v2/planning/ImplementationProgress-v2.md` — milestone tracker
