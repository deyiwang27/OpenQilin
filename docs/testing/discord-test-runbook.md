# OpenQilin Discord Test Runbook

Use this to start the runtime and test through Discord.

---

## Prerequisites

- Docker compose stack running (`postgres`, `redis`, `opa`, `litellm`)
- `.env` configured with API keys and Discord bot tokens
- `.secrets/discord_role_bot_tokens.json` with all required role-bot tokens

Verify infrastructure:
```bash
docker compose --profile core ps
```

---

## Step 1 — Apply migrations

```bash
set -a && source .env && set +a
uv run python -m alembic upgrade head
```

---

## Step 2 — Bootstrap (first run only)

```bash
set -a && source .env && set +a
uv run python -m openqilin.apps.admin_cli bootstrap --smoke-in-process
```

Expected output:
```
[OK] migrate: migrations applied to head
[OK] pgvector_extension: pgvector extension is available
[OK] smoke_owner_command_ingress_in_process: ...
```

---

## Step 3 — Start all workers

Run each in a separate terminal (or as background processes):

```bash
# Terminal 1 — Control plane API (port 8000)
set -a && source .env && set +a
uv run python -m uvicorn openqilin.apps.api_app:app --host 0.0.0.0 --port 8000

# Terminal 2 — Orchestrator worker
set -a && source .env && set +a
uv run python -m openqilin.apps.orchestrator_worker

# Terminal 3 — Communication worker
set -a && source .env && set +a
uv run python -m openqilin.apps.communication_worker

# Terminal 4 — Discord bot worker
set -a && source .env && set +a
uv run python -m openqilin.apps.discord_bot_worker
```

Verify API is up:
```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

---

## Step 4 — Discord smoke tests

Send these messages in any allowed Discord channel, in order:

### 4.1 Basic Secretary response
```
Hello, what can you do?
```
Expected: Secretary responds with a summary of capabilities.

### 4.2 Free-text question
```
What is the status of this system?
```
Expected: Secretary or routed agent responds.

### 4.3 Create a project
```
/oq create project "Website Redesign"
```
Expected: Project proposal is created.

Then initialize the approved project as CWO (governance flow). Once initialization succeeds, OpenQilin auto-creates a Discord text channel named `project-website-redesign` and persists an active project-space binding; PM responses should route in that channel immediately.

### 4.4 Check project status
```
/oq status
```
Expected: Summary of active projects and their state.

### 4.5 Governance gate test (budget-sensitive action)
```
/oq create project "Large AI Workflow" with budget 10000
```
Expected: CSO or CEO governance review triggered; approval required before project starts.

### 4.6 Audit trail check
After any interaction, check the audit panel in Grafana:
- Open `http://localhost:3000` (or your Grafana URL)
- Open the OpenQilin dashboard
- Verify governance events and task activity appear

---

## Troubleshooting

| Symptom | Check |
|---|---|
| Bot doesn't respond | Check `/tmp/oq_discord.log` for errors |
| No agent reply after Secretary | Check `/tmp/oq_orchestrator.log` |
| Discord message sent but no delivery | Check `/tmp/oq_comm.log` |
| OPA policy denied | Check audit_events table in PostgreSQL |
| `missing required role-bot tokens` | Add missing token to `.secrets/discord_role_bot_tokens.json` |

---

## Stopping all workers

```bash
pkill -f "uvicorn openqilin"
pkill -f "orchestrator_worker"
pkill -f "communication_worker"
pkill -f "discord_bot_worker"
```
