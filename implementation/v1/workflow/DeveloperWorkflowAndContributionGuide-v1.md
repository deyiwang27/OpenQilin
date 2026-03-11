# OpenQilin v1 - Developer Workflow and Contribution Guide

## 1. Scope
- Define the standard developer workflow from environment bootstrap to merge.

## 2. Daily Workflow
1. Sync dependencies with `uv sync`.
2. Install Git hooks once per clone with `uv run pre-commit install --hook-type pre-commit --hook-type pre-push`.
3. Bring up the authoritative local stack with Docker Compose.
4. Run the one-shot bootstrap/readiness gate when the environment is fresh or schema changes require it (after admin bootstrap command is implemented beyond scaffold placeholder behavior).
5. Run the target app or worker locally only when using a non-container developer loop; otherwise use the running Compose services.
6. Execute the smallest relevant test slice before opening a PR.

## 3. Standard Command Loop
```bash
uv sync
docker compose --profile full up -d
docker compose run --rm admin bootstrap
docker compose ps
uv run pytest tests/unit tests/component
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

Current scaffold note:
- `openqilin.apps.admin_cli` command handlers (`migrate`, `bootstrap`, `smoke`, `diagnostics`) are placeholders and must be implemented before treating bootstrap/smoke results as production-like readiness evidence.

Optional non-container app loop after dependencies are available:
```bash
uv run python -m openqilin.apps.api_app
uv run python -m openqilin.apps.orchestrator_worker
uv run python -m openqilin.apps.communication_worker
```

## 4. Branch and PR Rules
- follow `implementation/v1/workflow/GitHubOperationsManagementGuide-v1.md` as the canonical branch/issue/PR operations policy
- follow `implementation/v1/workflow/RepositoryConsistencyAndGovernanceCheck-v1.md` for structure/authority/folder-fit checks
- work on short-lived branches from latest `main` using `<type>/<issue-id>-<short-slug>`
- keep PR scope narrow to one coherent change set
- every PR links at least one issue
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
- `design/TODO.txt` is the historical tracker for design-stage work
- `design/v1/architecture/ContainerizationAndLocalInfraTopology-v1.md` is the authoritative local bring-up contract
- GitHub execution operations are governed by `implementation/v1/workflow/GitHubOperationsManagementGuide-v1.md`
- day-to-day human+Codex execution loop is governed by `implementation/v1/workflow/AIAssistedDeliveryWorkflow-v1.md`
- periodic structure/conflict/self-consistency review is governed by `implementation/v1/workflow/RepositoryConsistencyAndGovernanceCheck-v1.md`
