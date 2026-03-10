# OpenQilin v1 - Developer Workstation and Prerequisites

## 1. Scope
- Define the non-code prerequisites required before v1 implementation starts.
- Distinguish mandatory manual setup from services that should run in containers.
- Provide operator-facing setup steps for local development.

## 2. v1 Principle
Local-first implementation should prefer containerized dependencies over manual host installation.

Preferred local posture:
- install a small host toolchain
- run infrastructure dependencies through Docker Compose

## 3. Required Host Tools
Mandatory on developer workstation:
- `git`
- `uv`
- Docker with Compose support
- a POSIX shell environment (`zsh`/`bash`)

Recommended:
- `make` or `just` if later adopted for task shortcuts
- `psql` client for debugging Postgres
- `redis-cli` for debugging Redis

## 4. Infrastructure Prerequisite Decision
For initial v1 implementation:
- PostgreSQL: run in Docker, not manual host install
- Redis: run in Docker, not manual host install
- OPA: run in Docker, not manual host install
- OpenTelemetry Collector: run in Docker, not manual host install
- Grafana stack: run in Docker, not manual host install
- LiteLLM runtime: run in Docker or as one repo-managed app process

Kubernetes posture:
- not required for initial v1 implementation and local testing
- explicitly out of scope for workstation baseline
- revisit only for later promotion or ops topology design

## 5. Manual Setup Required From You
These items require manual action outside the repo.

### 5.1 Install `uv`
Reference:
- official install path depends on OS/environment

Typical macOS shell flow:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify:
```bash
uv --version
```

### 5.2 Install Docker
Choose one supported local container runtime path:
- Docker Desktop
- Colima + Docker CLI

Minimum requirement:
- `docker compose` must work locally

Verify:
```bash
docker --version
docker compose version
```

### 5.3 Create Gemini API Access For Initial Testing
Manual tasks:
- create or use a Google AI/Gemini developer account
- generate an API key suitable for free-tier testing
- store the key outside the repo

Expected local secret name:
- `GEMINI_API_KEY`

Do not:
- commit secrets into the repository
- place raw keys in tracked config files

### 5.4 Create Discord Developer Application
Manual tasks:
- create a Discord application
- create/configure the bot or interaction app
- capture required IDs/secrets:
  - application ID
  - public key
  - bot token if needed by chosen integration mode
  - guild/channel allowlist IDs

Expected local secret/config names:
- `DISCORD_APPLICATION_ID`
- `DISCORD_PUBLIC_KEY`
- `DISCORD_BOT_TOKEN` if required

### 5.5 Verify Container Runtime Can Pull/Run Baseline Services
You should be able to start local containers for:
- PostgreSQL
- Redis
- OPA
- OTel Collector
- Grafana

## 6. What You Do Not Need To Install Manually
Not required as host installs for v1 baseline:
- PostgreSQL server
- Redis server
- OPA binary
- Grafana server
- Kubernetes / `kubectl`

These should be containerized unless later design explicitly changes that posture.

## 7. Expected Local Service Baseline
Local Docker composition should eventually provide:
- `api_app`
- `orchestrator_worker`
- `communication_worker`
- `postgres`
- `redis`
- `opa`
- `otel_collector`
- `grafana`
- supporting trace/log backends if selected

## 8. Manual Preparation Checklist
- install `uv`
- install Docker with Compose support
- create Gemini API key for free-tier testing
- create Discord developer application and collect credentials
- confirm local container runtime works

## 9. Related Design Follow-Ups
- container topology details belong in `ContainerizationAndLocalInfraTopology-v1.md`
- environment variable and secret naming belongs in `ConfigurationAndEnvironmentModel-v1.md`
- bootstrap commands belong in `BootstrapAndMigrationWorkflow-v1.md`
