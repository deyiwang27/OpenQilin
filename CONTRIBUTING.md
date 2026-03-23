# Contributing to OpenQilin

Thank you for your interest in contributing to OpenQilin — a governed AI operating system for the solopreneur.

This guide covers how to set up the project, how the codebase is organised, where to start, and how to submit a pull request.

---

## How to set up

**Prerequisites:**
- Python 3.12
- [`uv`](https://github.com/astral-sh/uv) (Python package and environment manager)
- Docker Compose

**Steps:**

```bash
# 1. Clone the repository
git clone https://github.com/deyiwang89/OpenQilin.git
cd OpenQilin

# 2. Install all dependencies (including dev groups)
uv sync --all-groups

# 3. Copy the environment config and fill in your values
cp .env.example .env
# Minimum required: set OPENQILIN_GEMINI_API_KEY or configure an alternative LLM backend.

# 4. Start core infrastructure (PostgreSQL, Redis, OPA)
docker compose --profile core up -d

# 5. Apply database migrations
uv run alembic upgrade head

# 6. Validate the setup
uv run python -m openqilin.apps.oq_doctor
# All checks should pass before running tests.

# 7. Run the test suite
uv run pytest tests/unit tests/component
# Expected: all tests pass with no failures.
```

You do not need Discord credentials or a live LLM API key to run the unit and component test suite. The test tier that requires live infrastructure (`tests/integration`, `tests/contract`) needs the full compose stack — see below.

**Full compose stack (optional — for integration tests):**

```bash
docker compose --profile core up -d   # PostgreSQL, Redis, OPA
docker compose --profile obs up -d    # OTel, Prometheus, Tempo, Loki, Grafana
uv run pytest tests/unit tests/component tests/contract tests/integration
```

---

## How the codebase is organised

OpenQilin is split into two long-running processes:

- **Control plane** (`src/openqilin/apps/api_app.py`) — FastAPI app that receives Discord webhooks, classifies intent, and enqueues tasks.
- **Orchestrator worker** (`src/openqilin/apps/orchestrator_worker.py`) — Async worker that drains the task queue through a LangGraph pipeline.

Key source packages:

| Package | What it does |
|---|---|
| `src/openqilin/control_plane/` | FastAPI routers, intent grammar, identity checks, dependency wiring |
| `src/openqilin/task_orchestrator/` | LangGraph pipeline, loop controls, task dispatch |
| `src/openqilin/agents/` | All 9 institutional agent roles |
| `src/openqilin/data_access/repositories/postgres/` | PostgreSQL-backed persistence |
| `src/openqilin/policy_runtime_integration/` | OPA client and Rego policy bundle |
| `src/openqilin/observability/` | OpenTelemetry tracing, audit writer, metrics |
| `src/openqilin/shared_kernel/` | Settings, error types, startup validation |
| `constitution/` | OPA Rego bundle and YAML governance rules |
| `spec/` | Implementation contracts and architecture docs |

For a deeper orientation, read in this order:
1. [`README.md`](README.md) — product overview
2. [`spec/architecture/ArchitectureBaseline-v1.md`](spec/architecture/ArchitectureBaseline-v1.md) — runtime architecture
3. [`design/v2/README.md`](design/v2/README.md) — design decisions and ADRs
4. [`implementation/v2/planning/ImplementationProgress-v2.md`](implementation/v2/planning/ImplementationProgress-v2.md) — what is built and what is planned

---

## Where to start

Browse issues labelled [`good first issue`](https://github.com/deyiwang89/OpenQilin/issues?q=is%3Aopen+label%3A%22good+first+issue%22) — each one has a concrete scope, context, and expected outcome.

If you want to explore before picking up an issue:

- Read a role contract in `spec/governance/roles/` to understand how an agent is specified.
- Trace how a Discord message becomes a task: `control_plane/routers/discord_ingress.py` → `control_plane/grammar/` → `control_plane/handlers/`.
- Read an existing agent implementation: `src/openqilin/agents/secretary/` is the simplest.
- Run the test suite and read a test file: `tests/unit/test_m16_wp5_loop_token.py` is a recent, well-commented example.

---

## How to submit a PR

**Branch naming:**

```
<type>/<issue-id>-<short-slug>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore`

Examples: `feat/42-add-slack-adapter`, `fix/67-secretary-routing`, `docs/88-contributing-guide`

**Before opening a PR, run:**

```bash
# Governance gate — must return no output (merge blocker if any match)
grep -r --include="*.py" -l "class InMemory" . | grep -v "/testing/" | grep -v "tests/" | grep -v "/.venv/"

# Static checks
uv run ruff check .
uv run ruff format --check .
uv run mypy .

# Tests
uv run pytest tests/unit tests/component
```

**PR format:**
- Title: short (under 70 characters), imperative tense ("add X", "fix Y", "update Z")
- Body: summary of what changed and why; link to the GitHub issue
- All PRs merge to `main` via squash merge

**Review expectations:**
- The Architect (Claude) reviews for spec alignment and governance constraints.
- The Owner merges to main.
- Expect feedback within a few days. Small, focused PRs move faster than large ones.

---

## Code of conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold it.
