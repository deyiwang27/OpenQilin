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

## WP M18-WP5 — Deterministic Advisory Topic Router

**Goal:** Replace Secretary's prompt-only advisory routing with a two-tier deterministic system. Tier 1 is an `AdvisoryTopicRouter` — a keyword→agent authority table that resolves unambiguous routing without an LLM call. When Tier 1 matches, `discord_ingress.py` delegates directly to the target agent's `handle_free_text()` and returns its response. When Tier 1 has no match, Secretary's LLM (Tier 2) handles the message as today. Channel availability is enforced: Auditor and Administrator are not reachable in project channels; Secretary returns a natural-language referral with `/oq ask <role>` guidance. Secretary discovers live bot @mention handles from the Redis bot registry (`openqilin:bot_discord_ids`) to include `<@id>` mentions in referral messages.

**GitHub issue:** #207

**Entry gate:** M18-WP1 done ✓ (all agents have `handle_free_text()`), M18-WP2 done ✓

---

### Background

After M18-WP1, all agents have `handle_free_text()`. Secretary currently routes advisory queries by LLM-prompt alone — fragile because the LLM may route budget questions to CSO, strategic questions to PM, etc. A prompt fix was applied as a temporary measure (session 2026-03-23) but the owner confirmed this is not a durable solution. This WP installs a deterministic pre-filter that handles unambiguous cases without an LLM call, and enforces the authoritative routing table below regardless of LLM output.

**Authority table (owner-confirmed, 2026-03-23):**

| Agent | Topic domain | Keywords (case-insensitive substring match) |
|---|---|---|
| `auditor` | Budget, spend, compliance, violations, audit trail | budget, spend, spending, compliance, violation, audit, trail, financial, expenditure, cost, overrun, breach, governance breach |
| `cso` | Strategic alignment, portfolio, cross-project risks | strategic, strategy, portfolio, alignment, cross-project, opportunity, conflict, risk, roadmap |
| `project_manager` | Project status, tasks, assignments, milestones | task, assignment, blocked, milestone, progress, execution plan, sprint, backlog |
| `cwo` | Workforce, charter, specialist activation | charter, workforce, initialization, specialist, workforce plan, role binding, agent activation |
| `ceo` | Executive directives, approvals, escalation | approve, directive, executive, authorize, escalation, final decision |

Secretary is NOT a routing target in Tier 1 — Secretary's LLM handles its own fallback (Tier 2).

**Channel availability:**
- Project channels (channel bound to a project via `routing_resolver`): `{secretary, ceo, cwo, cso, project_manager}` are available
- Restricted roles (not available in project channels): `{auditor, administrator}`
- Determination: `is_project_channel = (routing_context is not None)` — `routing_context` comes from `routing_resolver.resolve(guild_id, channel_id)` already called in `discord_ingress.py`

**Bot registry Redis hash:**
- Key: `openqilin:bot_discord_ids`
- Field: role string (e.g., `"auditor"`, `"secretary"`)
- Value: Discord user ID string (e.g., `"1234567890"`)
- Write: each bot writes its own entry to this hash when `on_ready()` fires in `discord_bot_worker.py`
- Read: `BotRegistryReader` in `discord_ingress.py` formats `<@user_id>` for referral messages

---

### Tasks

#### New package: `src/openqilin/control_plane/advisory/`

- [ ] Create `src/openqilin/control_plane/advisory/__init__.py` (empty)
- [ ] Create `src/openqilin/control_plane/advisory/topic_router.py`:
  - `TOPIC_ROUTING_TABLE: dict[str, frozenset[str]]` — maps agent role to frozenset of lowercase keyword strings (use the authority table above; do not include `secretary` or `administrator` as routing targets)
  - `@dataclass(frozen=True, slots=True) class RoutingDecision` with fields `agent_role: str`, `confidence: Literal["high", "low"]`, `matched_keywords: list[str]`
  - `class AdvisoryTopicRouter` with `classify(self, text: str) -> RoutingDecision | None`:
    - Lowercase `text` before matching
    - For each role in `TOPIC_ROUTING_TABLE`, count how many keywords appear as substrings in the lowercased text
    - If exactly one role has ≥1 match: return `RoutingDecision(agent_role=role, confidence="high", matched_keywords=[...])`
    - If multiple roles match with equal counts: return `None` (let Secretary LLM decide tie-breaks)
    - If multiple roles match but one has strictly more matches: return that role with `confidence="high"`
    - If no role matches: return `None`
- [ ] Create `src/openqilin/control_plane/advisory/channel_availability.py`:
  - `CHANNEL_RESTRICTED_ROLES: frozenset[str] = frozenset({"auditor", "administrator"})`
  - `def is_role_available_in_channel(role: str, is_project_channel: bool) -> bool` — returns `False` if `is_project_channel` and `role in CHANNEL_RESTRICTED_ROLES`, else `True`
- [ ] Create `src/openqilin/control_plane/advisory/bot_registry_reader.py`:
  - `BOT_REGISTRY_REDIS_KEY = "openqilin:bot_discord_ids"`
  - `class BotRegistryReader` with constructor `__init__(self, redis_client: Any)` (accepts a Redis client — same type as used in `RedisIdempotencyCacheStore`, i.e., `redis.Redis`)
  - `def get_mention(self, role: str) -> str | None` — calls `self._redis.hget(BOT_REGISTRY_REDIS_KEY, role)`, decodes bytes if needed, returns `f"<@{user_id}>"` or `None` if missing; must not raise on Redis error — log warning and return `None`
  - `def get_all(self) -> dict[str, str]` — calls `self._redis.hgetall(BOT_REGISTRY_REDIS_KEY)`, decodes all keys/values, returns `{role: user_id}` dict; returns `{}` on error

#### Bot registry write: `src/openqilin/apps/discord_bot_worker.py`

- [ ] Import `build_redis_client` from `openqilin.data_access.repositories.postgres.idempotency_cache_store` (already imported in `dependencies.py`; add to bot worker)
- [ ] Add optional `redis_client: Any | None = None` parameter to `OpenQilinDiscordClient.__init__()` — store as `self._redis_client`
- [ ] In `OpenQilinDiscordClient.on_ready()`, after `mark_ready()`, add bot registry write:
  ```python
  if self._redis_client is not None and bot_user_id != "unknown":
      try:
          self._redis_client.hset("openqilin:bot_discord_ids", self._config.bot_role, bot_user_id)
          LOGGER.info("discord.worker.bot_registry_written", role=self._config.bot_role, user_id=bot_user_id)
      except Exception:
          LOGGER.warning("discord.worker.bot_registry_write_failed", role=self._config.bot_role)
  ```
- [ ] In `main()` (or wherever `OpenQilinDiscordClient` is instantiated), build a Redis client and pass it:
  ```python
  _redis = build_redis_client(settings.redis_url) if settings.redis_url else None
  ```
  Pass `redis_client=_redis` to each `OpenQilinDiscordClient(...)` constructor call.

#### Routing intercept: `src/openqilin/control_plane/routers/discord_ingress.py`

- [ ] Import `AdvisoryTopicRouter` from `openqilin.control_plane.advisory.topic_router`
- [ ] Import `is_role_available_in_channel` from `openqilin.control_plane.advisory.channel_availability`
- [ ] Import `BotRegistryReader` from `openqilin.control_plane.advisory.bot_registry_reader`
- [ ] Add `get_advisory_topic_router` and `get_bot_registry_reader` to `dependencies.py` and import them here
- [ ] Add `advisory_topic_router: AdvisoryTopicRouter = Depends(get_advisory_topic_router)` and `bot_registry_reader: BotRegistryReader = Depends(get_bot_registry_reader)` as parameters to `submit_discord_message()`
- [ ] In the free-text branch, **before** the block that calls `secretary_agent.handle()` when `resolved_target == "secretary"` (currently around line 455), add Tier 1 intercept:

  ```python
  # Tier 1: deterministic advisory topic routing (M18-WP5)
  _tier1 = advisory_topic_router.classify(content) if advisory_topic_router is not None else None
  if _tier1 is not None:
      _is_project_channel = routing_context is not None
      if is_role_available_in_channel(_tier1.agent_role, _is_project_channel):
          # Delegate to target agent directly
          _scope = f"guild::{payload.guild_id}::channel::{payload.channel_id}"
          _advisory_req = FreeTextAdvisoryRequest(
              text=content,
              scope=_scope,
              guild_id=payload.guild_id,
              channel_id=payload.channel_id,
              addressed_agent=_tier1.agent_role,
          )
          try:
              if _tier1.agent_role == "ceo":
                  _resp = ceo_agent.handle_free_text(_advisory_req)
              elif _tier1.agent_role == "cwo":
                  _resp = cwo_agent.handle_free_text(_advisory_req)
              elif _tier1.agent_role == "auditor":
                  _resp = auditor_agent.handle_free_text(_advisory_req)
              elif _tier1.agent_role == "cso":
                  _resp = cso_agent.handle_free_text(_advisory_req)
              elif _tier1.agent_role == "project_manager":
                  _resp = project_manager_agent.handle_free_text(_advisory_req)
              else:
                  _resp = None
              if _resp is not None:
                  return _discord_advisory_response(payload=payload, command="ask", message=_resp.advisory_text)
          except Exception:
              LOGGER.exception("discord_ingress.tier1_routing.agent_failed", target_role=_tier1.agent_role)
              # Fall through to Secretary LLM on exception
      else:
          # Role not available in this channel type — return referral
          _role_label = _tier1.agent_role.replace("_", " ").title()
          _mention = bot_registry_reader.get_mention(_tier1.agent_role) if bot_registry_reader is not None else None
          _mention_str = f" {_mention}" if _mention else ""
          _referral_msg = (
              f"The {_role_label} agent{_mention_str} is not available in project channels. "
              f"Use `/oq ask {_tier1.agent_role} <your question>` in a general channel."
          )
          return _discord_advisory_response(payload=payload, command="ask", message=_referral_msg)
  # Fall through to Secretary LLM (Tier 2) — unchanged path below
  ```

#### RuntimeServices and dependency wiring: `src/openqilin/control_plane/api/dependencies.py`

- [ ] Import `AdvisoryTopicRouter` from `openqilin.control_plane.advisory.topic_router`
- [ ] Import `BotRegistryReader` from `openqilin.control_plane.advisory.bot_registry_reader`
- [ ] Add `advisory_topic_router: AdvisoryTopicRouter` and `bot_registry_reader: BotRegistryReader` fields to `RuntimeServices` dataclass
- [ ] In `build_runtime_services()`:
  - `advisory_topic_router = AdvisoryTopicRouter()` (no constructor arguments)
  - `bot_registry_reader = BotRegistryReader(redis_client=redis_client)` (Redis client already built at this point as `redis_client`)
- [ ] Add to the `return RuntimeServices(...)` call: `advisory_topic_router=advisory_topic_router, bot_registry_reader=bot_registry_reader`
- [ ] Add dependency getter functions:
  ```python
  def get_advisory_topic_router(request: Request) -> AdvisoryTopicRouter:
      return get_runtime_services(request).advisory_topic_router

  def get_bot_registry_reader(request: Request) -> BotRegistryReader:
      return get_runtime_services(request).bot_registry_reader
  ```

#### Tests

- [ ] Create `tests/unit/advisory/__init__.py` (empty)
- [ ] Create `tests/unit/advisory/test_topic_router.py`:
  - `test_classify_budget_keyword` — text "what is my budget?" → `RoutingDecision(agent_role="auditor", confidence="high", ...)`
  - `test_classify_spend_keyword` — text "show spend report" → auditor
  - `test_classify_strategic_keyword` — text "portfolio alignment?" → cso
  - `test_classify_task_keyword` — text "what tasks are blocked?" → project_manager
  - `test_classify_charter_keyword` — text "project charter status" — note "project" is in project_manager keywords and "charter" is in cwo keywords; verify most-matches wins or tie → None
  - `test_classify_no_match` — text "hello how are you" → `None`
  - `test_classify_case_insensitive` — text "BUDGET COMPLIANCE" → auditor
  - `test_classify_most_matches_wins` — text with 2 auditor keywords, 1 cso keyword → auditor
  - `test_classify_tie_returns_none` — text with exactly 1 match for 2 different roles → `None`
- [ ] Create `tests/unit/advisory/test_channel_availability.py`:
  - `test_auditor_not_in_project_channel` — `is_role_available_in_channel("auditor", True)` → `False`
  - `test_administrator_not_in_project_channel` — `is_role_available_in_channel("administrator", True)` → `False`
  - `test_auditor_in_general_channel` — `is_role_available_in_channel("auditor", False)` → `True`
  - `test_cso_in_project_channel` — `is_role_available_in_channel("cso", True)` → `True`
  - `test_secretary_in_project_channel` — `is_role_available_in_channel("secretary", True)` → `True`
- [ ] Create `tests/unit/advisory/test_bot_registry_reader.py`:
  - `test_get_mention_present` — mock Redis `hget` returns `b"1234567890"` → `"<@1234567890>"`
  - `test_get_mention_bytes` — mock returns `b"9876543210"` (bytes) → decoded correctly
  - `test_get_mention_absent` — mock returns `None` → `None`
  - `test_get_mention_redis_error` — mock raises exception → returns `None` (no propagation)
  - `test_get_all_returns_dict` — mock returns `{b"auditor": b"123", b"cso": b"456"}` → `{"auditor": "123", "cso": "456"}`
  - `test_get_all_redis_error` — mock raises exception → returns `{}`
- [ ] Create `tests/unit/test_m18_wp5_tier1_router.py` (secretary + ingress integration):
  - `test_tier1_high_confidence_routes_to_auditor` — mock `AdvisoryTopicRouter.classify()` returns auditor high-confidence, `routing_context=None` (non-project channel); verify `auditor_agent.handle_free_text()` called with original text; verify advisory response returned
  - `test_tier1_restricted_role_in_project_channel` — mock returns auditor, `routing_context` non-None (project channel); verify referral message returned, auditor NOT called
  - `test_tier1_no_match_falls_through_to_secretary` — mock returns `None`; verify `secretary_agent.handle()` called as before
  - `test_tier1_agent_exception_falls_through` — mock returns cso but `cso_agent.handle_free_text()` raises; verify fall-through to Secretary (no uncaught exception)
  - `test_tier1_router_unavailable` — `advisory_topic_router=None` in dependencies; verify Secretary path used normally
- [ ] Static checks: `ruff`, `mypy`, InMemory grep gate, `pytest tests/unit tests/component` pass

---

### Key interfaces (spec)

```python
# topic_router.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

TOPIC_ROUTING_TABLE: dict[str, frozenset[str]] = {
    "auditor": frozenset({
        "budget", "spend", "spending", "compliance", "violation", "audit",
        "trail", "financial", "expenditure", "cost", "overrun", "breach",
        "governance breach",
    }),
    "cso": frozenset({
        "strategic", "strategy", "portfolio", "alignment", "cross-project",
        "opportunity", "conflict", "risk", "roadmap",
    }),
    "project_manager": frozenset({
        "task", "assignment", "blocked", "milestone", "progress",
        "execution plan", "sprint", "backlog",
    }),
    "cwo": frozenset({
        "charter", "workforce", "initialization", "specialist",
        "workforce plan", "role binding", "agent activation",
    }),
    "ceo": frozenset({
        "approve", "directive", "executive", "authorize", "escalation",
        "final decision",
    }),
}

@dataclass(frozen=True, slots=True)
class RoutingDecision:
    agent_role: str
    confidence: Literal["high", "low"]
    matched_keywords: list[str] = field(default_factory=list)

class AdvisoryTopicRouter:
    def classify(self, text: str) -> RoutingDecision | None: ...
```

```python
# channel_availability.py
CHANNEL_RESTRICTED_ROLES: frozenset[str] = frozenset({"auditor", "administrator"})

def is_role_available_in_channel(role: str, is_project_channel: bool) -> bool:
    if is_project_channel and role in CHANNEL_RESTRICTED_ROLES:
        return False
    return True
```

```python
# bot_registry_reader.py
BOT_REGISTRY_REDIS_KEY = "openqilin:bot_discord_ids"

class BotRegistryReader:
    def __init__(self, redis_client: Any) -> None: ...
    def get_mention(self, role: str) -> str | None: ...
    def get_all(self) -> dict[str, str]: ...
```

---

### Outputs

- `src/openqilin/control_plane/advisory/` — new package (3 modules + `__init__.py`)
- Updated `src/openqilin/apps/discord_bot_worker.py` — Redis bot registry write in `on_ready()`
- Updated `src/openqilin/control_plane/routers/discord_ingress.py` — Tier 1 intercept in Secretary free-text path
- Updated `src/openqilin/control_plane/api/dependencies.py` — `advisory_topic_router`, `bot_registry_reader` wired into `RuntimeServices`
- `tests/unit/advisory/` — new test suite (3 modules)
- `tests/unit/test_m18_wp5_tier1_router.py` — integration-style unit tests

### Done criteria

- [x] Sending "what's my budget?" as free text in a non-project channel → Auditor responds directly (Tier 1 match, no Secretary LLM call)
- [x] Sending "portfolio strategy alignment?" → CSO responds directly (Tier 1)
- [x] Ambiguous or unmatched text → Secretary LLM advisory (Tier 2, unchanged)
- [x] Budget-related free text in a project channel → Secretary returns referral message, Auditor NOT called
- [x] Referral message includes `<@id>` if bot registry has the entry, falls back to role name if not
- [x] Bot registry Redis hash updated when each bot comes online (`on_ready()`)
- [x] `AdvisoryTopicRouter` or `BotRegistryReader` None → graceful fallback, no crash
- [x] `ruff`, `mypy`, InMemory grep gate, `pytest tests/unit tests/component` all pass
- [x] No regression on `/oq ask <agent> <text>` explicit commands or `@everyone` broadcast

---

## M18 Exit Criteria

- [ ] All five WPs above are marked done
- [ ] Every institutional agent responds to @mentions with an LLM-generated conversational reply from its own identity
- [ ] `@everyone` triggers simultaneous introductions from all 7 agents
- [ ] Advisory routing is deterministic for unambiguous topic domains (Tier 1 keyword table)
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
