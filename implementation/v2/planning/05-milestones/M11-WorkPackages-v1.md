# M11 Work Packages — Discord Grammar and Secretary Activation

Milestone: `M11`
Status: `planned`
Entry gate: M10 complete
Design ref: `design/v2/architecture/M11-DiscordGrammarAndSecretaryModuleDesign-v2.md`, `design/v2/components/ControlPlaneComponentDelta-v2.md`

---

## Milestone Goal

Replace JSON-shaped command entry with human-friendly free-text and compact command syntax. Activate Secretary as a real advisory front-desk agent. Wire LangSmith for dev-time LLM tracing. Fix the C-7 chat_class KeyError before any further agent surface work.

---

## WP M11-01 — Grammar Layer

**Goal:** Introduce the grammar package that classifies intent and parses commands before they reach the ingress pipeline.

**Design ref:** `design/v2/architecture/M11-DiscordGrammarAndSecretaryModuleDesign-v2.md §2–4`

**Entry criteria:** Existing Discord ingress (`discord_ingress.py`) works end-to-end; no grammar layer exists yet.

### Tasks

- [ ] Create `src/openqilin/control_plane/grammar/models.py` — `IntentClass` enum, `CommandEnvelope`, `RoutingHint` dataclasses
- [ ] Implement `grammar/intent_classifier.py` — classify message into `discussion | query | mutation | admin`; call LLM gateway for free-text classification; reject `mutation` from free text with `GRAM-004`
- [ ] Implement `grammar/command_parser.py` — parse `/oq <verb> [target] [args]` into `CommandEnvelope`; raise `GrammarParseError` on unrecognized verb
- [ ] Implement `grammar/free_text_router.py` — resolve routing target from chat class, project binding context, and explicit mention; default to `secretary` for unroutable discussion in institutional channels
- [ ] Wire grammar layer into `routers/discord_ingress.py` — call grammar before building ingress payload; explicit `/oq` bypasses free-text classifier
- [ ] Wire grammar layer in `api/dependencies.py`

### Outputs

- `src/openqilin/control_plane/grammar/` package (4 modules)
- Grammar layer called on every Discord inbound message before ingress

### Done criteria

- [ ] Valid `/oq submit task "do X"` returns correct `CommandEnvelope`
- [ ] Unrecognized verb raises `GrammarParseError` → 400
- [ ] Free-text `mutation`-classified message rejected with `GRAM-004` validation error before reaching `CommandHandler`
- [ ] Free-text `discussion` in institutional channel resolves routing to `secretary`

---

## WP M11-02 — C-7 Security Fix: `chat_class` KeyError

**Goal:** Fix the `KeyError` → 500 crash when an unknown `chat_class` value is received in `discord_governance.py`.

**Bug ref:** C-7 | **Design ref:** `design/v2/components/ControlPlaneComponentDelta-v2.md §1.2`

**Entry criteria:** Bug reproducible by sending a message with an unrecognized `chat_class` value.

### Tasks

- [x] In `src/openqilin/control_plane/identity/discord_governance.py`: replace `_MEMBERSHIP_BY_CHAT_CLASS[chat_class]` with `.get(chat_class)` and raise `GovernanceDenialError` when `None`
- [x] Add unit test: unknown `chat_class` → 403 `GovernanceDenialError`, not 500 `KeyError`

### Outputs

- Single-line fix in `discord_governance.py`
- One new unit test

### Done criteria

- [x] Sending unknown `chat_class` returns 403 with `governance_denial` payload
- [x] No `KeyError` raised in any code path for unknown `chat_class`

---

## WP M11-03 — Secretary Agent Activation

**Goal:** Wire Secretary as a real advisory-only responder in institutional shared channels.

**Design ref:** `design/v2/architecture/M11-DiscordGrammarAndSecretaryModuleDesign-v2.md §3`

**Entry criteria:** WP M11-01 complete (grammar layer routes `discussion` to secretary); Secretary agent scaffold exists or is created here.

### Tasks

- [ ] Create `src/openqilin/agents/secretary/` package: `agent.py`, `prompts.py`, `models.py`
- [ ] Implement `SecretaryAgent.handle(request)` — advisory-only responses: intent disambiguation, routing suggestions, daily digest summaries
- [ ] Bind advisory-only policy profile in `agent.py` — `allow` for `advisory` axis, `deny` for all mutation axes; Secretary MUST NOT issue commands or mutate state
- [ ] Wire `SecretaryAgent` in `api/dependencies.py`; inject into grammar routing path
- [ ] Confirm Secretary is a participant in `leadership_council`, `executive`, `governance` channels per `OwnerInteractionModel.md` MVP v2 active profile
- [ ] Add integration test: Secretary handles `discussion` intent and returns advisory response; attempted mutation request is rejected before any state change

### Outputs

- `src/openqilin/agents/secretary/` package
- Secretary active as real responder (not placeholder)

### Done criteria

- [ ] `discussion` message in `leadership_council` receives Secretary advisory response
- [ ] Secretary cannot trigger any state-mutating action (rejected by advisory policy profile)
- [ ] Secretary is NOT activated as default responder in project channels

---

## WP M11-04 — LangSmith Dev-Time Tracing

**Goal:** Enable LangSmith tracing for LangGraph runs via environment variables. No code changes required — only `compose.yml` configuration.

**Design ref:** `design/v2/adr/ADR-0005-LangGraph-State-Machine-Adoption.md`, `design/v2/components/ObservabilityAndDashboardDelta-v2.md §1.3`

**Entry criteria:** LangGraph is not yet in `pyproject.toml` (wired in M13), but env vars can be pre-configured. This WP configures the vars now so they are ready when LangGraph is adopted.

### Tasks

- [x] Add to `compose.yml` under `orchestrator_worker` service:
  ```yaml
  LANGCHAIN_TRACING_V2: ${LANGCHAIN_TRACING_V2:-false}
  LANGCHAIN_API_KEY: ${LANGCHAIN_API_KEY:-}
  LANGCHAIN_PROJECT: ${LANGCHAIN_PROJECT:-openqilin-dev}
  ```
- [x] Add `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` to `.env.example` with default `false`/empty values
- [x] Add comment in `compose.yml` clarifying LangSmith is dev-time tracing only — not a governance audit source

### Outputs

- Updated `compose.yml`
- Updated `.env.example`

### Done criteria

- [x] LangSmith tracing can be enabled by setting `LANGCHAIN_TRACING_V2=true` in `.env` without code changes
- [x] Disabled by default (no LangSmith calls when env var is absent or `false`)

---

## M11 Exit Criteria

- [ ] All four WPs above are marked done
- [ ] Free-text and `/oq` command interactions work end to end in the real Discord stack
- [ ] Secretary is active and responds in institutional channels
- [ ] No JSON-shaped input required for any normal owner interaction
- [ ] Unknown `chat_class` returns 403, not 500
- [ ] No new InMemory placeholder introduced in a production code path

## References

- `design/v2/architecture/M11-DiscordGrammarAndSecretaryModuleDesign-v2.md`
- `design/v2/components/ControlPlaneComponentDelta-v2.md`
- `spec/orchestration/communication/OwnerInteractionGrammar.md`
- `spec/orchestration/communication/OwnerInteractionModel.md`
