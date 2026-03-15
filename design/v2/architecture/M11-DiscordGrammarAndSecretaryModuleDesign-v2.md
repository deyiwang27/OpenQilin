# OpenQilin v2 — M11 Module Design: Discord Grammar and Secretary Activation

Milestone: `M11 — Discord Surface, Chat UX, and Secretary Activation`
References: `design/v2/components/ControlPlaneComponentDelta-v2.md`, `spec/orchestration/communication/OwnerInteractionGrammar.md`

---

## 1. Scope

- Replace JSON-shaped command entry with free-text + compact command syntax (`/oq <verb> [target] [args]`).
- Introduce grammar layer: intent classification, command parsing, and free-text routing.
- Activate `secretary` as a real advisory-only responder.
- Integrate LangSmith as dev-time tracing overlay (env vars only, no governance coupling).
- Fix [C-7]: fail-closed guard for unknown `chat_class` in `discord_governance.py`.

Out of scope for M11:
- OPA wiring (M12)
- Project-space binding (M13)
- Role self-assertion fix (M12 prerequisite before Secretary and CSO get real authority)

---

## 2. Package Layout

### New packages

```text
src/openqilin/control_plane/grammar/
  __init__.py
  intent_classifier.py     ← classify inbound message into 4 intent classes
  command_parser.py        ← parse /oq compact command syntax → CommandEnvelope
  free_text_router.py      ← resolve routing target from chat class and project binding
  models.py                ← IntentClass enum, CommandEnvelope, RoutingHint dataclasses
```

### Modified files

```text
src/openqilin/control_plane/
  identity/
    discord_governance.py  ← fix C-7: .get() instead of [] for chat_class lookup
  api/
    dependencies.py        ← wire grammar layer, wire secretary agent
  routers/
    discord_ingress.py     ← call grammar layer before building ingress payload
src/openqilin/agents/
  secretary/
    __init__.py
    agent.py               ← Secretary agent: advisory-only, uses advisory policy profile
    prompts.py             ← intent disambiguation, daily digest, routing suggestion prompts
    models.py              ← SecretaryRequest, SecretaryResponse
```

### compose.yml additions

```yaml
orchestrator_worker:
  environment:
    LANGCHAIN_TRACING_V2: ${LANGCHAIN_TRACING_V2:-false}
    LANGCHAIN_API_KEY: ${LANGCHAIN_API_KEY:-}
    LANGCHAIN_PROJECT: ${LANGCHAIN_PROJECT:-openqilin-dev}
```

---

## 3. Runtime Responsibilities

### `grammar/intent_classifier.py`
- Classifies inbound Discord message into `IntentClass`: `discussion | query | mutation | admin`.
- Free-text classification uses LLM with a lightweight system prompt.
- `mutation` classified from free text is rejected at the grammar layer with `GRAM-004` (`validation_error: use explicit command syntax`).
- Explicit `/oq` command bypasses free-text classifier; intent is derived from verb.

### `grammar/command_parser.py`
- Parses compact syntax: `/oq <verb> [target] [args]`
- Returns `CommandEnvelope(verb, target, args, raw_input)`.
- Raises `GrammarParseError` on unrecognized verb or missing required argument.

### `grammar/free_text_router.py`
- Resolves routing target from: chat class, project binding context, and explicit mention.
- In institutional shared channels: routes to `secretary` for `discussion`, `query` for `query`.
- In project channels: routes to `project_manager` by default per GRAM-005.
- Falls back to `secretary` for unroutable free-text discussion in institutional channels.

### `agents/secretary/agent.py`
- Advisory-only policy profile: `allow` for `advisory` axis, `deny` for all mutation axes.
- Does not issue commands, mutate state, or act as delegation authority.
- Responds with: intent disambiguation, routing suggestions, daily digest summaries.
- Uses LangSmith tracing automatically when `LANGCHAIN_TRACING_V2=true`.

### `identity/discord_governance.py` fix (C-7)
```python
# Before (raises KeyError → 500):
allowed_members = _MEMBERSHIP_BY_CHAT_CLASS[chat_class]

# After (fail-closed → 403):
allowed_members = _MEMBERSHIP_BY_CHAT_CLASS.get(chat_class)
if allowed_members is None:
    raise GovernanceDenialError(f"unknown_chat_class: {chat_class}")
```

---

## 4. Key Interfaces

```python
# grammar/intent_classifier.py
class IntentClassifier:
    async def classify(self, message: str, context: ChatContext) -> IntentClass: ...

# grammar/command_parser.py
class CommandParser:
    def parse(self, raw_input: str) -> CommandEnvelope: ...

# grammar/free_text_router.py
class FreeTextRouter:
    async def resolve(self, intent: IntentClass, context: ChatContext) -> RoutingHint: ...

# agents/secretary/agent.py
class SecretaryAgent:
    async def handle(self, request: SecretaryRequest) -> SecretaryResponse: ...

# models.py
class IntentClass(str, Enum):
    DISCUSSION = "discussion"
    QUERY = "query"
    MUTATION = "mutation"
    ADMIN = "admin"

@dataclass
class CommandEnvelope:
    verb: str
    target: str | None
    args: dict[str, str]
    raw_input: str

@dataclass
class RoutingHint:
    target_role: str
    project_id: str | None
    confidence: float
```

---

## 5. Dependency Rules

- `grammar/` depends on `control_plane/identity/` (for chat context) — no upward dependency.
- `grammar/intent_classifier.py` may call LLM gateway for classification — uses existing `LlmGatewayClient`, not a direct LLM call.
- `agents/secretary/` depends on `policy_runtime_integration/` for advisory-profile enforcement.
- Secretary MUST NOT depend on `task_orchestrator/` mutation paths.
- `discord_ingress.py` calls grammar layer before building the ingress payload; the grammar result is an input to (not a bypass of) the existing ingress validation chain.
- LangSmith integration is ENV-VAR-ONLY — no import of `langsmith` SDK in production code paths; LangGraph emits traces automatically when env vars are set.

---

## 6. Testing Focus

| Test | Assertion |
|---|---|
| `intent_classifier`: `mutation` from free text | Returns `MUTATION`; router rejects with `GRAM-004` |
| `command_parser`: valid `/oq submit task "do X"` | Returns correct `CommandEnvelope` |
| `command_parser`: unknown verb | Raises `GrammarParseError` |
| C-7 fix: unknown `chat_class` | Returns 403 `GovernanceDenialError`, not 500 `KeyError` |
| `secretary`: handles `discussion` intent | Returns advisory response, no state mutation |
| `secretary`: attempted mutation request | Rejected by advisory policy profile before any state change |
| Grammar → ingress: end-to-end `/oq` command | Passes through grammar layer and reaches `CommandHandler` |

---

## 7. Related References

- `design/v2/components/ControlPlaneComponentDelta-v2.md`
- `design/v2/adr/ADR-0005-LangGraph-State-Machine-Adoption.md` (LangSmith env vars)
- `spec/orchestration/communication/OwnerInteractionGrammar.md`
- `spec/orchestration/communication/OwnerInteractionModel.md`
- `spec/constitution/AuthorityMatrix.yaml` (advisory policy profile for secretary)
