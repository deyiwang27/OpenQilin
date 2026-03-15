# OpenQilin v2 - Developer Workflow and Contribution Guide

Adapts `implementation/v1/workflow/DeveloperWorkflowAndContributionGuide-v1.md` for v2. Same toolchain and loop; v2-specific items marked **[v2]**.

---

## 1. Scope

Define the standard developer workflow from environment bootstrap to merge for MVP-v2.

---

## 2. Daily Workflow

1. Sync dependencies with `uv sync`.
2. Install Git hooks once per clone: `uv run pre-commit install --hook-type pre-commit --hook-type pre-push`.
3. Bring up the authoritative local stack with Docker Compose (full profile includes OPA, PostgreSQL, Redis, OTel, Grafana).
4. **[v2]** Run `oq-doctor` when the environment is fresh or infrastructure services have changed.
5. Run the target app or worker locally only when using a non-container developer loop; otherwise use running Compose services.
6. Execute the smallest relevant test slice before opening a PR.

---

## 3. Standard Command Loop

```bash
uv sync
docker compose --profile full up -d

# [v2] Validate all infrastructure connections
docker compose --profile doctor run oq_doctor

docker compose ps
uv run pytest tests/unit tests/component
uv run ruff check .
uv run ruff format --check .
uv run mypy .

# [v2] Run integration tests that require the compose stack
uv run pytest tests/integration -m "requires_compose"
```

**[v2] Alembic migration commands:**
```bash
# Apply all migrations on a fresh DB
uv run alembic upgrade head

# Check current migration status
uv run alembic current

# Generate a new migration (review carefully before committing)
uv run alembic revision --autogenerate -m "describe_the_change"
```

**[v2] OPA bundle commands:**
```bash
# Verify OPA is reachable and bundle loaded
curl http://localhost:8181/v1/data/openqilin/policy/version
curl http://localhost:8181/v1/health

# Evaluate a test policy request
curl -X POST http://localhost:8181/v1/data/openqilin/policy/decide \
  -H "Content-Type: application/json" \
  -d '{"input": {"principal_role": "owner", "action": "submit_task"}}'
```

Optional non-container app loop after dependencies are available:
```bash
uv run python -m openqilin.apps.api_app
uv run python -m openqilin.apps.orchestrator_worker
uv run python -m openqilin.apps.communication_worker
```

---

## 4. Branch and PR Rules

- follow `implementation/v2/workflow/GitHubOperationsManagementGuide-v2.md` as canonical branch/issue/PR operations policy
- follow `implementation/v2/workflow/RepositoryConsistencyAndGovernanceCheck-v2.md` for structure/authority/folder-fit checks
- work on short-lived branches from latest `main` using `<type>/<issue-id>-<short-slug>`
- keep PR scope narrow to one coherent change set
- every PR links at least one issue
- code changes that touch contracts or migrations must update design/spec references in the same PR
- PRs must include the exact local verification commands run

---

## 5. Test Expectations by Change Type

| Change type | Required tests |
|---|---|
| Module logic | Unit tests |
| Boundary/adapter | Component or contract tests |
| Governed path | Integration or conformance coverage |
| Schema change | Alembic forward-apply validation + regression coverage |
| OPA Rego change | Rego unit tests; OPA integration test |
| LangGraph graph | End-to-end graph test |
| Budget reservation | Concurrent integration test (locking behavior) |

---

## 6. Debugging Workflow

- use structured logs and `trace_id` first
- **[v2]** inspect Grafana/Tempo/Loki for end-to-end trace correlation (OTel is wired in v2)
- **[v2]** use `oq-doctor` output for infrastructure connectivity issues before diving into app logs
- use admin diagnostics commands for database and checkpoint inspection
- do not debug governed-path behavior from raw provider logs alone
- **[v2]** for OPA-related issues: check OPA container logs and `curl http://localhost:8181/v1/health`

---

## 7. Manual Preparation Checklist

Before serious implementation work:
1. Install `uv`
2. Install Docker and Compose
3. Create local `.env` file: copy `.env.example`, fill in Gemini API key, Discord bot token and secrets
4. **[v2]** Set `LANGCHAIN_TRACING_V2=false` (or configure LangSmith creds if dev tracing is desired)
5. Confirm Docker can start the full local stack: `docker compose --profile full up -d`
6. **[v2]** Run `docker compose --profile doctor run oq_doctor` — confirm all blocking checks pass

---

## 8. Documentation Hygiene

- `spec/` remains authoritative for contracts
- `design/v2/` remains authoritative for v2 implementation-facing design decisions
- `implementation/v2/planning/05-milestones/` is the task-level source of truth for v2 execution
- `implementation/v2/planning/ImplementationProgress-v2.md` is the in-repo WP-status mirror
- GitHub execution operations governed by `implementation/v2/workflow/GitHubOperationsManagementGuide-v2.md`
- day-to-day human+AI execution loop governed by `implementation/v2/workflow/AIAssistedDeliveryWorkflow-v2.md`
- periodic structure/consistency review governed by `implementation/v2/workflow/RepositoryConsistencyAndGovernanceCheck-v2.md`
