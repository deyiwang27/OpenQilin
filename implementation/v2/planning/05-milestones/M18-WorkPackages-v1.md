# M18 Work Packages — Conversational UX Completion

Milestone: `M18`
Status: `planned`
Entry gate: M17 complete (open-source readiness done; conversation memory foundation live)
Supporting docs: `design/v2/architecture/ConversationMemoryDesign-v1.md`

---

## Milestone Goal

Make every institutional agent a first-class conversational participant. After M17, Secretary is the only agent with an LLM-backed conversational mode — all others respond to @mentions with a static stub. M18 gives each agent its own role-appropriate advisory voice, backed by the PostgreSQL conversation store established in M17-WP8, and deployed through the same channel-routing infrastructure fixed in the M17 post-merge bug fixes.

---

## WP M18-01 — Conversational Advisory Mode for Institutional Agents

**Goal:** Give each institutional bot (CEO, CWO, Auditor, Administrator, CSO, Project Manager) its own LLM-backed conversational response when @mentioned with free text in Discord — the same pattern as Secretary's `_generate_advisory`, but from each agent's own role identity and perspective. All conversational responses are advisory only: no state mutations, no task dispatch, no identity verification required.

**Design ref:** `src/openqilin/agents/secretary/agent.py` (`_generate_advisory` pattern to replicate); `src/openqilin/control_plane/routers/discord_ingress.py` (secretary advisory bypass to generalize)

### Background

After M17-WP9 and the post-merge routing fixes, when a non-Secretary bot is @mentioned with free text in a group channel, that bot forwards the message to the control plane via `process_event()`. The control plane currently has no advisory bypass for non-Secretary agents — free-text to those agents falls through to the task-dispatch path, which requires principal identity verification and a structured task context. This WP adds an advisory bypass for all six institutional agents and gives each a role-appropriate LLM handler.

### Spec Gaps Identified (post-M17 testing)

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

PM is NOT a participant until the project reaches `approved` or `active` state. Routing a new-project discussion to PM is incorrect and misleads the owner about the approval process.

**Fix (task 0 below):** Update `ADVISORY_SYSTEM_PROMPT` to distinguish project creation (route to CWO; explain CSO → CEO → CWO gate flow) from existing project work (route to PM).

**Gap 2 — CEO, CWO, CSO conversational prompts must reflect the gate flow**

The conversational system prompts for CEO, CWO, and CSO (tasks 2, 3, 6 below) must accurately describe GATE-001 through GATE-005. Each agent's prompt must:
- CEO: explain it receives proposals after CSO strategic review (GATE-003); its role is co-review with CWO and approval at GATE-004
- CWO: explain it drafts the project charter and submits the proposal; leads workforce initialization at GATE-005 after approval
- CSO: explain it performs the first mandatory strategic review (GATE-001) before any CEO/CWO review; its outcomes are `Aligned`, `Needs Revision`, `Strategic Conflict`

**Gap 3 — Secretary routing advice for `executive`/`leadership_council` DISCUSSION intent**

`FreeTextRouter` routes DISCUSSION/QUERY in institutional channels to Secretary (correct per grammar spec). Secretary then advises. The prompt fix in Gap 1 ensures Secretary's advice matches the gate flow. No `FreeTextRouter` code change needed.

---

### Tasks

- [ ] **[Gap 1 fix]** Update `ADVISORY_SYSTEM_PROMPT` in `src/openqilin/agents/secretary/prompts.py`: distinguish new-project initiation (route to CWO; explain CSO → CEO → CWO gate sequence) from existing-project work (route to PM)
- [ ] Add `FreeTextAdvisoryRequest` and `FreeTextAdvisoryResponse` dataclasses to new module `src/openqilin/agents/shared/free_text_advisory.py`
- [ ] Add `handle_free_text()` method and conversational system prompt to `CeoAgent`; inject `conversation_store` into constructor
- [ ] Add `handle_free_text()` method and conversational system prompt to `CwoAgent`; inject `conversation_store` into constructor
- [ ] Add `handle_free_text()` method and conversational system prompt to `AuditorAgent`; inject optional `llm_gateway` and `conversation_store` into constructor
- [ ] Add `handle_free_text()` method and conversational system prompt to `AdministratorAgent`; inject optional `llm_gateway` and `conversation_store` into constructor
- [ ] Add `handle_free_text()` method and conversational system prompt to `CSOAgent`; inject `conversation_store` into constructor
- [ ] Add `handle_free_text()` method and conversational system prompt to `ProjectManagerAgent`
- [ ] Generalize the secretary advisory bypass in `discord_ingress.py` to a six-agent routing block; gate on `payload.bot_role` to route each request to the correct agent's `handle_free_text()`
- [ ] Wire `llm_gateway` and `conversation_store` into Auditor and Administrator in `build_runtime_services()`; wire `conversation_store` into CEO, CWO, CSO, PM
- [ ] Handle `@everyone` broadcast: all 7 agents (including Secretary) respond simultaneously with their own intro when `@everyone` is used in a channel; implement via `is_everyone_mention` flag on `DiscordInboundEvent` — all bots process the event, each posts its own `handle_free_text()` response
- [ ] Unit tests for each agent's `handle_free_text()`: happy path, fallback path, store absent, store present
- [ ] Static checks pass: `ruff`, `mypy`, InMemory grep gate

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

**Prompt constraint for CEO, CWO, CSO (Gap 2):** Each prompt must explain the full gate sequence in plain language so that when an owner asks "how do I start a project?", the agent gives accurate gate-flow guidance rather than routing to PM.

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

The `payload.bot_role` field (already set by `discord_bot_worker.py`) identifies which bot forwarded the message and therefore which agent's handler to call.

### Conversation history (spec)

All `handle_free_text()` implementations use scope `f"guild::{guild_id}::channel::{channel_id}"` (M17-WP8 unified key). `list_turns()` before the LLM call; `append_turns()` after. The `agent_id` written is the agent's role string. This means all agents in the same channel share one contiguous conversation transcript — intentional per M17-WP8 design.

### Outputs

- `src/openqilin/agents/shared/free_text_advisory.py` — shared request/response dataclasses
- `_CONVERSATIONAL_SYSTEM_PROMPT` + `handle_free_text()` on each of: CeoAgent, CwoAgent, AuditorAgent, AdministratorAgent, CSOAgent, ProjectManagerAgent
- New `prompts.py` in `src/openqilin/agents/auditor/` and `src/openqilin/agents/administrator/`
- Updated `discord_ingress.py`: six-agent advisory bypass
- Updated `build_runtime_services()`: `llm_gateway` and `conversation_store` wired into all six agents
- Unit tests: 6 × 4 test cases minimum

### Done criteria

- [ ] @mentioning any institutional bot in a Discord group channel with free text triggers an LLM-generated, role-appropriate response posted by that agent's bot — not a canned stub, not Secretary
- [ ] @mentioning in a DM also triggers an advisory response
- [ ] Each agent's response correctly identifies itself (not Secretary) and gives role-specific guidance
- [ ] Conversation history is persisted and reused across turns (multi-turn test per agent)
- [ ] No `handle_free_text()` dispatches tasks or mutates state
- [ ] `/oq ask <agent>` and all explicit commands continue working (no regression)
- [ ] `ruff`, `mypy`, InMemory gate, `pytest tests/unit tests/component` all pass

---

## M18 Exit Criteria

- [ ] All WPs above are marked done
- [ ] Every institutional agent responds to @mentions with an LLM-generated conversational reply from its own identity
- [ ] Conversation memory persisted per channel across all agents
- [ ] No regression in existing task-dispatch or governance flows

## References

- `src/openqilin/agents/secretary/agent.py` — advisory pattern reference
- `design/v2/architecture/ConversationMemoryDesign-v1.md` — conversation store design
- `implementation/v2/planning/ImplementationProgress-v2.md` — milestone tracker
