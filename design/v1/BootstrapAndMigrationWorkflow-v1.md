# OpenQilin v1 - Bootstrap and Migration Workflow

## 1. Scope
- Define the local bootstrap workflow for first-run implementation and testing.
- Define database migration and seed data expectations.

## 2. First-Run Local Workflow
Expected developer path:
1. install workstation prerequisites
2. run `uv sync`
3. provide local environment variables/secrets
4. start local infrastructure with Docker Compose
5. run migrations
6. seed baseline data
7. start app processes
8. run smoke tests

## 3. Migration Workflow
Rules:
- schema changes are forward-only migrations
- migrations are executed by `admin_cli` or designated ops command
- migration files live under `migrations/`
- every schema change must have a corresponding validation step in CI

Local migration command shape:
```bash
uv run python -m openqilin.apps.admin_cli migrate
```

## 4. Seed and Bootstrap Data
Minimum seed set:
- lookup roles
- state dimensions
- baseline policy metadata references
- local test-safe configuration records if needed

Rules:
- seed data must be deterministic
- production secrets must never be part of bootstrap seed data
- bootstrap should be rerunnable without corrupting idempotent baseline records

## 5. Docker Compose Expectations
Compose baseline should support:
- infra startup before app startup
- health-checked dependencies
- named volumes for local persistence where useful
- optional clean reset flow for local development

## 6. Smoke Validation After Bootstrap
Minimum smoke checks:
- API app health endpoint
- orchestrator worker startup
- policy runtime reachable
- postgres reachable
- redis reachable
- audit/trace pipeline reachable enough for local validation

## 7. Recovery Notes
- bootstrap/reset flow must not bypass migration history
- local reset should be explicit and separate from normal startup
- recovery drills remain a later operational concern but bootstrap should not conflict with them

## 8. Related Design Follow-Ups
- process topology is defined in `AppEntrypointsAndProcessTopology-v1.md`
- workstation setup is defined in `DeveloperWorkstationAndPrerequisites-v1.md`
- CI migration checks are defined in `CICDAndQualityGateDesign-v1.md`
