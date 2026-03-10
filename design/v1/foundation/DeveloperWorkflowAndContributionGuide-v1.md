# OpenQilin v1 - Developer Workflow and Contribution Guide

## 1. Scope
- Define the standard developer workflow from environment bootstrap to merge.

## 2. Daily Workflow
1. Sync dependencies with `uv sync`.
2. Start required local services with Docker Compose.
3. Run migrations and seed baseline data when schema changes require it.
4. Run the target app or worker locally.
5. Execute the smallest relevant test slice before opening a PR.

## 3. Standard Command Loop
```bash
uv sync
uv run python -m openqilin.apps.admin_cli migrate
uv run python -m openqilin.apps.admin_cli seed
uv run python -m openqilin.apps.api_app
uv run pytest tests/unit tests/component
uv run ruff check .
uv run mypy .
```

## 4. Branch and PR Rules
- work on short-lived branches
- keep PR scope narrow to one coherent change set
- code changes that touch contracts or migrations must update design/spec references in the same PR
- PRs should include the exact local verification commands run

## 5. Test Expectations by Change Type
- module logic change: unit tests
- boundary/adapter change: component or contract tests
- governed path change: integration or conformance coverage
- schema change: forward-apply migration validation and regression coverage

## 6. Debugging Workflow
- use structured logs and `trace_id` first
- inspect Grafana/Tempo/Loki in the `full` profile for end-to-end issues
- use admin diagnostics commands for database, outbox, and checkpoint inspection
- do not debug governed-path behavior from raw provider logs alone

## 7. Manual Preparation Checklist
Before serious implementation work, you still need to:
1. install `uv`
2. install Docker and Compose
3. create local `.env` files with Gemini and Discord credentials
4. confirm Docker can start the full local stack

## 8. Documentation Hygiene
- `spec/` remains authoritative for contracts
- `design/` remains authoritative for implementation-facing design decisions
- `design/TODO.txt` is the live tracker for design-stage work
