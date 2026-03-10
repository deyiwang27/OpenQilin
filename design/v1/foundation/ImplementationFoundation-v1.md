# OpenQilin v1 - Implementation Foundation

## 1. Scope
- Define the non-feature foundation required before implementation.
- Consolidate toolchain, workstation prerequisites, configuration model, and bootstrap workflow.

## 2. Python Toolchain Baseline
Python runtime baseline:
- Python `3.12`

Dependency and environment manager:
- `uv`

Authoritative project metadata:
- root `pyproject.toml`
- root `uv.lock`

Rules:
- `pyproject.toml` is the only source of truth for Python dependencies
- `uv.lock` is committed
- `requirements.txt` is not the primary dependency artifact
- local commands run through `uv run ...`

Minimum dependency groups:
- `default`
- `dev`
- `test`
- `lint`
- `ops`

Standard commands:
```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

## 3. Developer Workstation Prerequisites
Mandatory host tools:
- `git`
- `uv`
- Docker with Compose support
- POSIX shell environment

Recommended local posture:
- install a small host toolchain
- run infrastructure dependencies in containers

Manual setup required from you:
1. Install `uv`
2. Install Docker / Compose
3. Create Gemini API key for free-tier testing
4. Create Discord developer application and capture required credentials
5. Verify local container runtime can run baseline services

Typical macOS `uv` install:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verification:
```bash
uv --version
docker --version
docker compose version
```

## 4. Local Infrastructure Baseline
Preferred local dependency posture:
- PostgreSQL: Docker
- Redis: Docker
- OPA: Docker
- OTel Collector: Docker
- Grafana stack: Docker
- LiteLLM: Docker or repo-managed app process

Not required for initial v1 local-first implementation:
- Kubernetes / `kubectl`
- host-installed Postgres/Redis/OPA/Grafana servers

Expected local secret names:
- `GEMINI_API_KEY`
- `DISCORD_APPLICATION_ID`
- `DISCORD_PUBLIC_KEY`
- `DISCORD_BOT_TOKEN` when required

## 5. Configuration and Environment Model
Environments:
- `local_dev`
- `ci`
- `staging`
- `production`

Configuration precedence:
1. process environment variables
2. environment-specific local config files not committed with secrets
3. checked-in non-secret defaults

Key config domains:
- runtime: `OPENQILIN_ENV`, logging, trace sampling
- identity/connectors: Discord IDs/tokens and allowlists
- data: `POSTGRES_DSN`, `REDIS_URL`
- governance: `OPA_BASE_URL`
- llm gateway: `OPENQILIN_LLM_ROUTING_PROFILE`, `LITELLM_BASE_URL`, `GEMINI_API_KEY`
- observability: OTLP endpoint and dashboard backend endpoints

Rules:
- secrets never live in committed config files
- startup validates required config by app role
- missing required governed-path config fails closed

## 6. Bootstrap and Migration Workflow
Expected first-run flow:
1. install prerequisites
2. run `uv sync`
3. provide local env vars/secrets
4. start the long-running local stack with `docker compose --profile full up -d`
5. run the one-shot readiness gate with `docker compose run --rm admin bootstrap`
6. use the running stack for local development and tests

Authoritative rule:
- the exact local full-stack bring-up contract is defined in `design/v1/architecture/ContainerizationAndLocalInfraTopology-v1.md`
- bootstrap, migration, seed, and smoke behavior must converge on the `admin bootstrap` one-shot command in implementation

Migration rules:
- schema changes are forward-only
- migrations live under `migrations/`
- migrations are executed by `admin_cli` or equivalent ops entrypoint

Seed rules:
- deterministic baseline data only
- no production secrets in bootstrap data
- bootstrap must be rerunnable without duplicating baseline records

Local migration command shape:
```bash
uv run python -m openqilin.apps.admin_cli migrate
```

Compose-first readiness command shape:
```bash
docker compose --profile full up -d
docker compose run --rm admin bootstrap
```

## 7. Related Follow-Ups
- architecture and module map live in `design/v1/architecture/ImplementationArchitecture-v1.md`
- authoritative local bring-up lives in `design/v1/architecture/ContainerizationAndLocalInfraTopology-v1.md`
- quality and delivery details live in `design/v1/quality/QualityAndDelivery-v1.md`
