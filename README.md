# OpenQilin

A governed AI operating system for the solopreneur — delegate work to an AI workforce through Discord, with constitutional policy enforcement, real cost visibility, and an immutable audit trail.

## What is OpenQilin?

OpenQilin turns one capable person into a coordinated AI-augmented team by giving each agent role a bounded authority, a policy-gated action space, and a cost-tracked budget. It treats authority, policy, audit, and project-state transitions as runtime constraints, not after-the-fact documentation — every agent action is authorised by a live OPA policy engine, recorded immutably in PostgreSQL, and cost-tracked before it executes.

## Why?

- **Coordination noise** — solopreneurs managing AI agents through chat lose track of who decided what, who approved it, and why. OpenQilin gives every decision a governance record.
- **Cost opacity** — LLM spend is invisible until the bill arrives. OpenQilin tracks and enforces a per-project budget before each action, using a real cost model backed by PostgreSQL.
- **Role sprawl** — without explicit authority boundaries, agents either do too little (asking for approval on every step) or too much (acting outside their mandate). OpenQilin enforces constitutional roles end-to-end.

## How it works

- You interact through Discord using natural language or `/oq` commands; a grammar layer classifies intent and routes it to the correct agent role
- Every action is evaluated by an OPA policy engine against a versioned constitutional bundle before it executes — the system is fail-closed by default
- A LangGraph orchestration pipeline handles admission, obligation checking, budget approval, and agent dispatch in sequence
- Project state, conversation history, budget ledger, task execution records, and audit events are all persisted in PostgreSQL
- Grafana dashboards give real-time visibility into project health, budget consumption, agent activity, and governance events

## Status

MVP-v2 is complete. All core agents are active:

| Agent | Role |
|---|---|
| **Secretary** | Routes and summarises Discord interactions; advisory-only |
| **CSO** (Chief Strategy Officer) | Portfolio governance advisor |
| **Domain Leader** | Project-space coordinator and escalation point |
| **Project Manager** | Task planning and specialist dispatch |
| **CEO** | Directive authority with co-approval enforcement |
| **CWO** (Chief Workflow Officer) | Command authority; project charter writes |
| **Auditor** | Compliance monitoring and behavioural violation detection |
| **Administrator** | Agent lifecycle, document policy, and retention enforcement |
| **Specialist** | Task execution against project goals |

Infrastructure: OPA policy runtime · PostgreSQL persistence · Redis idempotency · OpenTelemetry tracing · Grafana dashboards · file-backed artifact storage.

Full milestone tracker: [`implementation/v2/planning/ImplementationProgress-v2.md`](implementation/v2/planning/ImplementationProgress-v2.md)

## Quick Start

**Prerequisites:** Python 3.12, [`uv`](https://github.com/astral-sh/uv), Docker Compose

### 1. Clone and install

```bash
git clone https://github.com/deyiwang89/OpenQilin.git
cd OpenQilin
uv sync --all-groups
```

### 2. Configure environment

```bash
cp .env.example .env
# Required: set OPENQILIN_GEMINI_API_KEY (or configure a different LLM backend).
# Optional: set Discord bot credentials if you want a real Discord integration.
# See .env.example for all settings with descriptions.
```

### 3. Start infrastructure and run migrations

```bash
docker compose --profile core up -d
uv run alembic upgrade head
```

### 4. Validate setup

```bash
uv run python -m openqilin.apps.oq_doctor
# All checks should pass before starting the runtime.
```

### 5. Bootstrap and start

```bash
uv run python -m openqilin.apps.admin_cli bootstrap --smoke-in-process

# In separate terminals:
uv run python -m openqilin.apps.api_app
uv run python -m openqilin.apps.orchestrator_worker
uv run python -m openqilin.apps.communication_worker
uv run python -m openqilin.apps.discord_bot_worker   # optional: real Discord bot
```

### Full container stack

```bash
docker compose --profile full up -d
```

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest tests/unit tests/component
```

## Architecture

OpenQilin runs as two long-running processes:

- **Control plane** (`api_app`) — FastAPI app that receives Discord webhooks, authenticates callers, classifies intent, and enqueues tasks.
- **Orchestrator worker** — Async worker that drains the task queue through a LangGraph pipeline: policy evaluation → obligation check → budget approval → agent dispatch.

Read more: [`spec/architecture/ArchitectureBaseline-v1.md`](spec/architecture/ArchitectureBaseline-v1.md)

Source layout:

| Path | Contents |
|---|---|
| `constitution/` | OPA Rego policy bundle and YAML governance rules |
| `spec/` | Implementation contracts and authoritative architecture docs |
| `src/openqilin/` | Python runtime: control_plane, task_orchestrator, agents, data_access, observability |
| `tests/` | Unit, component, contract, integration, and conformance coverage |
| `migrations/` | Alembic schema migrations |
| `ops/` | Docker stack config, Grafana dashboards, OTel collector |

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

Apache 2.0 — see [LICENSE](LICENSE).
