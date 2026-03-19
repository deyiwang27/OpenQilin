# OpenQilin

OpenQilin is a governance-first multi-agent runtime for operating a long-running AI workforce.
It treats authority, policy, audit, budget, and project-state transitions as runtime constraints, not after-the-fact documentation.

## What OpenQilin Is

- A control plane for governed AI work, built around explicit roles such as `owner`, `administrator`, `auditor`, `ceo`, `cwo`, `project_manager`, `domain_leader`, and `specialist`
- A fail-closed orchestration runtime with constitutional policy enforcement, immutable audit evidence, and durable project artifacts
- A local-first implementation stack using FastAPI, LangGraph, PostgreSQL, Redis, OPA, OpenTelemetry, and file-backed storage
- A repo where `constitution/`, `spec/`, and implementation code stay tightly linked so behavior is traceable to written rules

## Current Status

OpenQilin is in active implementation, not just planning.

- Milestones `M11` through `M14` are complete, including Secretary, CSO, Project Manager, CEO, CWO, Auditor, Administrator, Specialist, and file-backed artifact storage.
- Milestones `M15` through `M17` are planned next, covering budget persistence, runtime polish, and public open-source readiness.
- The canonical in-repo status tracker is [`implementation/v2/planning/ImplementationProgress-v2.md`](implementation/v2/planning/ImplementationProgress-v2.md).

This means the repo already contains a working control plane, workers, governance agents, persistence layer, migrations, and tests. The public-facing packaging is still being improved.

## Runtime Overview

At a high level, the runtime is organized like this:

- `src/openqilin/control_plane/`: FastAPI routers, request schemas, identity/governance checks, dependency wiring
- `src/openqilin/task_orchestrator/`: admission, dispatch, LangGraph workflow, lifecycle handling
- `src/openqilin/agents/`: institutional and project-role agents
- `src/openqilin/data_access/repositories/postgres/`: PostgreSQL-backed repositories and persistence adapters
- `src/openqilin/policy_runtime_integration/rego/`: OPA policy bundle used by the policy runtime
- `src/openqilin/apps/`: runnable entrypoints for the API, workers, and admin CLI

## Quick Start

Prerequisites:

- Python `3.12`
- [`uv`](https://github.com/astral-sh/uv)
- Docker Compose

### 1. Install dependencies

```bash
uv sync --all-groups
```

### 2. Create local environment config

```bash
cp .env.example .env
```

Notes:

- Set `OPENQILIN_GEMINI_API_KEY` if you want to use the Gemini-backed LLM path.
- Set Discord bot credentials only if you plan to run the Discord worker.
- Keep `OPENQILIN_SYSTEM_ROOT` outside the source tree.

### 3. Start core infrastructure

```bash
docker compose --profile core up -d
uv run alembic upgrade head
uv run python -m openqilin.apps.admin_cli bootstrap --smoke-in-process
```

### 4. Run the app locally

Use the local developer loop when you want fast iteration without running every service in containers:

```bash
uv run python -m openqilin.apps.api_app
uv run python -m openqilin.apps.orchestrator_worker
uv run python -m openqilin.apps.communication_worker
```

Optional:

```bash
uv run python -m openqilin.apps.discord_bot_worker
```

### 5. Run the full container stack

If your `.env` is fully configured and you want the complete local runtime:

```bash
docker compose --profile full up -d
```

## Development Checks

Run these before opening or updating a PR:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest tests/unit tests/component
```

Useful admin commands:

```bash
uv run python -m openqilin.apps.admin_cli diagnostics --check-db
uv run python -m openqilin.apps.admin_cli smoke --in-process
```

## Repository Map

- `constitution/`: runtime constitutional rules and versioned policy bundles
- `spec/`: implementation contracts and authoritative architecture/specification docs
- `design/`: design artifacts and implementation-facing technical decisions
- `implementation/`: milestone planning, handoffs, workflow guides, and progress tracking
- `src/`: Python runtime implementation
- `tests/`: unit, component, contract, integration, and conformance coverage
- `migrations/`: Alembic migrations
- `ops/`: local stack, observability, and operational scripts

Document precedence:

1. `constitution/`
2. `spec/`
3. `design/`
4. `docs/`

## Start Reading Here

If you are new to the project, use this order:

1. [`docs/SystemOverview.md`](docs/SystemOverview.md)
2. [`docs/QuickStart.md`](docs/QuickStart.md)
3. [`spec/architecture/ArchitectureBaseline-v1.md`](spec/architecture/ArchitectureBaseline-v1.md)
4. [`spec/governance/architecture/GovernanceArchitecture.md`](spec/governance/architecture/GovernanceArchitecture.md)
5. [`spec/infrastructure/architecture/RuntimeArchitecture.md`](spec/infrastructure/architecture/RuntimeArchitecture.md)
6. [`constitution/core/PolicyManifest.yaml`](constitution/core/PolicyManifest.yaml)
7. [`implementation/v2/planning/ImplementationProgress-v2.md`](implementation/v2/planning/ImplementationProgress-v2.md)

## License

OpenQilin is licensed under the terms of the [LICENSE](LICENSE) file.
