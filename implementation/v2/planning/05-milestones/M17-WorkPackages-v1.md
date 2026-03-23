# M17 Work Packages — Open-Source and Sponsorship Readiness

Milestone: `M17`
Status: `planned`
Entry gate: M16 complete (full runtime polished and stable)
Supporting docs: `03-community/OpenSourceCommunityStrategy-v1.md`, `03-community/FundingAndSponsorshipStrategy-v1.md`

---

## Milestone Goal

Prepare OpenQilin for public introduction, early contributors, and realistic sponsorship and startup-credit outreach. The runtime is complete; this milestone makes it presentable, discoverable, and inviting. Every deliverable here should be usable for real outreach before or immediately after public launch.

---

## WP M17-01 — Public README and Repository Clarity

**Goal:** Make the repository understandable to a first-time visitor in under 10 minutes. Replace any internal-only framing with a clear public product story.

**Design ref:** `03-community/OpenSourceCommunityStrategy-v1.md §4.2`

### Tasks

- [x] Write root `README.md` with sections:
  - **What is OpenQilin?** — 2-sentence product thesis: governed AI operating system for the solopreneur
  - **Why?** — pain it solves: coordination noise, cost opacity, role sprawl
  - **How it works** — 3-5 bullet overview: Discord surface + constitutional governance + project-space routing + Grafana visibility
  - **Status** — MVP-v2 complete; Secretary/CSO/DL/PM/CEO/CWO/Auditor/Administrator/Specialist activation
  - **Quick start** — prerequisites, `docker compose up`, first interaction
  - **Architecture** — link to `spec/architecture/ArchitectureBaseline-v1.md`
  - **Roadmap** — link to roadmap doc (WP M17-02)
  - **Contributing** — link to `CONTRIBUTING.md` (WP M17-04)
  - **License** — confirm license file present (`LICENSE`)
- [x] Ensure `LICENSE` file exists (MIT or Apache 2.0; confirm with project owner) — Apache 2.0 confirmed present
- [x] Review and update `compose.yml` and environment variable docs to reflect the real MVP-v2 topology (not v1 placeholder comments)
- [x] Review `spec/` directory: confirm no internal-only or placeholder docs are exposed without clear status labels — grep returned no matches

### Outputs

- Clear, public-facing `README.md`
- `LICENSE` file present
- Compose and env docs accurate for the real MVP-v2 stack

### Done criteria

- [x] A new visitor can understand what OpenQilin is, why it exists, and how to try it in under 10 minutes of repo exploration
- [x] Quick start actually works end-to-end on a clean machine
- [x] No stale internal-only framing in root-visible files — WP-reference comments removed from compose.yml and .env.example

---

## WP M17-02 — Roadmap

**Goal:** Publish a public roadmap that makes OpenQilin's direction legible and investable for contributors and potential sponsors.

**Design ref:** `03-community/OpenSourceCommunityStrategy-v1.md §4.3`

### Tasks

- [x] Create `ROADMAP.md` at repo root with:
  - **Completed (MVP-v1)** — what v1 proved: institutional role presence, project governance, governed tool flows
  - **Completed (MVP-v2)** — what v2 delivers: real OPA enforcement, PostgreSQL persistence, LangGraph orchestration, Grafana dashboard, free-text UX, Secretary/CSO/DL activation
  - **Next (post-MVP-v2)** — high-level directions: full sandbox isolation, broader chat adapter support, OpenQilin console, sponsor/community growth
  - **Non-goals** — what OpenQilin is deliberately not: general AI framework, multi-user SaaS, code generation tool
- [x] Keep roadmap items as themes/goals, not deadlines

### Outputs

- `ROADMAP.md` at repo root
- Linked from `README.md`

### Done criteria

- [x] Roadmap is legible to an external reader with no prior context
- [x] MVP-v2 items are marked complete
- [x] Post-MVP directions are framed as themes, not timelines

---

## WP M17-03 — Demo Assets

**Goal:** Create a reusable, convincing end-to-end demo that showcases the solopreneur use case. Demo should work for outreach, README, and presentations.

**Design ref:** `03-community/OpenSourceCommunityStrategy-v1.md §4.2`

### Tasks

- [ ] Write demo script: one concrete solopreneur workflow end-to-end:
  1. Owner creates a project via Discord (`/oq create project "Website Redesign"`)
  2. PM responds in project space; DL escalation visible when needed
  3. Budget allocation visible in Grafana Budget panel
  4. CSO governance gate visible on a policy-sensitive action
  5. Owner views blocked task and approves in Discord
  6. Audit trail visible in Grafana Audit panel
- [ ] Record demo as screen recording (or animated GIF for README) — narrated or captioned
- [ ] Write companion `docs/demo/` folder with step-by-step text walkthrough usable in README and outreach
- [ ] Confirm demo runs on a clean `docker compose up` without manual setup beyond `.env` config

### Outputs

- Demo script and screen recording / GIF
- `docs/demo/` walkthrough text
- Demo runnable from clean checkout

### Done criteria

- [ ] Demo showcases governance, project execution, budget visibility, and audit trail
- [ ] Demo runs on clean checkout without prior context
- [ ] Demo asset usable in GitHub README, social media post, and sponsorship deck

---

## WP M17-04 — Contributor Entry Path

**Goal:** Make it possible for an external contributor to find, understand, and begin contributing to OpenQilin without needing private context.

**Design ref:** `03-community/OpenSourceCommunityStrategy-v1.md §4.4`

### Tasks

- [x] Write `CONTRIBUTING.md`:
  - **How to set up** — prerequisites, clone, `docker compose up`, run tests
  - **How the codebase is organized** — link to `spec/architecture/ArchitectureBaseline-v1.md` and `design/v2/README.md`
  - **Where to start** — point to `good first issue` label; suggest reading path
  - **How to submit a PR** — branch naming, PR format, review expectations
  - **Code of conduct** — short, standard CoC or link to `CODE_OF_CONDUCT.md`
- [x] Write `CODE_OF_CONDUCT.md` (Contributor Covenant or equivalent)
- [x] Label 3–5 existing issues as `good first issue` in GitHub with clear descriptions
- [x] Confirm test suite runs cleanly from a clean clone: `pytest` passes without manual data seeding

### Outputs

- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- 3–5 labeled `good first issue` GitHub issues

### Done criteria

- [x] External contributor can set up and run tests in under 30 minutes using `CONTRIBUTING.md` alone
- [x] At least 3 `good first issue` issues exist with scope, context, and expected outcome described
- [x] `CONTRIBUTING.md` linked from `README.md`

---

## WP M17-05 — Website and Public Presence

**Goal:** Establish a minimal public web presence with a domain, landing page, and contact email. Required for sponsorship applications and contributor discovery.

**Design ref:** `03-community/FundingAndSponsorshipStrategy-v1.md §4.2`

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

## WP M17-06 — Sponsorship and Startup-Credit Readiness

**Goal:** Prepare the minimum assets needed to apply to startup and sponsorship programs credibly.

**Design ref:** `03-community/FundingAndSponsorshipStrategy-v1.md §4`

### Tasks

- [x] Write one-page project summary (PDF or Markdown → PDF):
  - What OpenQilin is and who it is for
  - What MVP-v2 delivers
  - Current traction (GitHub stars, contributors if any, demo link)
  - What resources would unlock (compute, LLM API credits, infra)
  - Contact info
- [x] Identify and shortlist target programs to apply to:
  - AWS Activate / Google for Startups (cloud compute credits)
  - GitHub Sponsors (community funding)
  - Anthropic / Google / relevant LLM provider developer programs
  - Open-source foundation grants if eligible
- [x] Set up GitHub Sponsors profile (even if starting at $0)
- [x] Add FUNDING.yml to repo root pointing to GitHub Sponsors

### Outputs

- One-page project summary asset
- Target program shortlist
- GitHub Sponsors profile active
- `FUNDING.yml` in repo root

### Done criteria

- [x] One-page summary ready to attach to any program application
- [x] GitHub Sponsors profile live (even at zero sponsors)
- [x] `FUNDING.yml` in repo root
- [x] At least one sponsorship/credit program application submitted or scheduled

---

## WP M17-07 — Auto-create Discord Project Channel on Initialization

**Goal:** When a CWO initializes an approved project, automatically create a Discord project channel and persist an active `project_space_bindings` record so routing is live immediately.

**Design ref:** `implementation/handoff/current.md` (M17-WP7 handoff; issue #168)

### Tasks

- [x] Replace `DiscordChannelAutomator.create_channel()` stub with a real Discord REST API call using `settings.discord_bot_token`
- [x] Add optional `guild_id` field to `ProjectInitializationRequest`
- [x] Wire `ProjectSpaceBindingService` into `RuntimeServices` and expose `get_binding_service` dependency
- [x] Update governance initialization endpoint to call `binding_service.create_and_bind(...)` after successful project init
- [x] Make channel creation failure non-fatal (project initialization still succeeds; failure logged)
- [x] Add unit tests for Discord automator success/error paths and initialize-project binding behavior
- [x] Update Discord testing runbook to document auto-created project channel behavior

### Outputs

- Real Discord channel creation in `project_spaces/discord_automator.py`
- Auto-binding on project initialization in governance router
- New unit tests for automator and initialization binding behavior
- Updated Discord runbook notes for initialization flow

### Done criteria

- [x] `initialize_project` with `guild_id` creates and binds a project channel (success path)
- [x] `initialize_project` without `guild_id` skips binding cleanly
- [x] Any channel creation/binding exception is caught and logged without failing initialization
- [x] Static checks and unit/component tests pass with the new wiring

---

## WP M17-08 — Conversation Memory Foundation

**Goal:** Establish unified per-channel conversation scope, increase the hot window from 6 to 40 rows (20 exchanges), and introduce windowed warm-tier summarization so all agents in a channel share a coherent transcript.

**Design ref:** `design/v2/architecture/ConversationMemoryDesign-v1.md`

### Tasks

- [x] Unify conversation scope key: replace `"{project}::{guild}::{channel}::{thread}::{role}::{agent_id}"` with `"guild::{guild_id}::channel::{channel_id}"` in `LlmGatewayDispatchAdapter._conversation_scope()`
- [x] Align Secretary scope: update `discord_ingress.py` to pass the unified scope key (not `"discord:{channel_id}"`)
- [x] Increase `max_turns` from 6 to 40 and add `ConversationMemoryConfig` dataclass
- [x] Alembic migration: add `agent_id TEXT` and `window_index INTEGER` to `conversation_messages`
- [x] Alembic migration: create `conversation_windows` table
- [x] Implement `list_windows(scope)` and `fetch_window(scope, window_index)` in `PostgresConversationStore`
- [x] Synchronous window summary generation on window close (injected `summarize_fn`, non-fatal)
- [x] Update `_compose_role_locked_prompt()` to include warm summaries before hot turns
- [x] Update unit and component tests

### Done criteria

- [x] All agents in the same channel share one `conversation_messages` scope
- [x] Warm summaries generated and loaded after a window fills (40 rows)
- [x] `max_turns=40` default; old `max_turns=6` removed
- [x] Static checks and unit/component tests pass (829 passed)

---

## WP M17-09 — Semantic Fetch and Agent Tool

**Goal:** Give agents autonomous context retrieval — proactive semantic pre-fetch of relevant cold windows before each LLM call, and a reactive tool for mid-reasoning history lookup. Add cross-channel summary fetch for on-demand context from other channels or DMs.

**Design ref:** `design/v2/architecture/ConversationMemoryDesign-v1.md`

### Tasks

- [ ] Add `summary_embedding vector(1536)` column to `conversation_windows` (Alembic migration)
- [ ] Add `ivfflat` index on `summary_embedding` using `vector_cosine_ops`
- [ ] Async embedding generation for window summaries (background task after summary write)
- [ ] Implement `find_relevant_windows(scope, query_embedding, threshold, limit)` via pgvector ANN
- [ ] Wire proactive semantic pre-fetch into `LlmGatewayDispatchAdapter.load_context()`
- [ ] Register `get_conversation_window(window_index, scope?)` as LangGraph tool for all async agents
- [ ] Implement `fetch_channel_summary(target_scope)` in store
- [ ] Wire `/oq context from:#channel-name` command in `discord_ingress.py`
- [ ] Add `context_sources: list[str]` field to `TaskPayload`
- [ ] Wire proactive semantic pre-fetch into Secretary sync path
- [ ] Integration tests (require postgres + pgvector)

### Done criteria

- [ ] Agent receives relevant cold window content without user prompting (proactive fetch)
- [ ] Agent can call `get_conversation_window` tool mid-reasoning
- [ ] `/oq context from:#channel` attaches summary to next invocation
- [ ] DM scope cross-channel fetch restricted to participating bot only
- [ ] Integration tests pass with compose stack

---

## M17 Exit Criteria

- [ ] All nine WPs above are marked done
- [ ] README, CONTRIBUTING.md, CODE_OF_CONDUCT.md, ROADMAP.md all live in repo root
- [ ] Demo runs end-to-end on clean checkout
- [ ] Public domain and contact email live
- [ ] GitHub Sponsors profile active
- [ ] At least one sponsorship/credit program application submitted
- [ ] A new visitor can understand, try, and begin contributing to OpenQilin without prior context

## References

- `03-community/OpenSourceCommunityStrategy-v1.md`
- `03-community/FundingAndSponsorshipStrategy-v1.md`
- `00-direction/MvpV2SuccessCriteria-v1.md §4.8`
