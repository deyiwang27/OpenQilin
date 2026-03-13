# M10 Live Multi-Bot Discord Acceptance Checklist

Date: `2026-03-13`  
Milestone: `M10 Multi-Bot Discord Role UI`  
Work package: `M10-WP6` (`#67`)

## 1. Goal

Validate live Discord behavior for multi-bot role UI:
- DM to each role bot resolves to that role
- mention-driven group chat triggers only explicitly mentioned role bots
- outbound long replies are complete (chunked, non-truncated) and readable

## 2. Preconditions

- Docker CLI/daemon available.
- Discord role-bot tokens are configured in:
  - `OPENQILIN_DISCORD_MULTI_BOT_ENABLED=true`
  - `OPENQILIN_DISCORD_ROLE_BOT_TOKENS_FILE` (recommended)
  - `OPENQILIN_DISCORD_ROLE_BOT_TOKENS_JSON`
  - `OPENQILIN_DISCORD_REQUIRED_ROLE_BOTS_CSV`
- Required role bots are present and invited to target guild:
  - `administrator`, `auditor`, `ceo`, `cwo`, `project_manager`
- Gemini API key configured for `llm_reason` path:
  - `OPENQILIN_GEMINI_API_KEY`
- Connector secret configured:
  - `OPENQILIN_CONNECTOR_SHARED_SECRET`

## 3. Runtime Boot

1. `docker compose --profile full up -d --build`
2. Verify health:
   - `api_app`, `orchestrator_worker`, `communication_worker`, `discord_bot_worker`
3. Capture startup logs:
   - `docker compose logs api_app --tail=200`
   - `docker compose logs discord_bot_worker --tail=400`

## 4. Live Scenarios

### 4.1 Direct Message Matrix
For each role bot (`administrator`, `auditor`, `ceo`, `cwo`, `project_manager`):
1. Open DM with role bot account.
2. Send governed command (`/oq {"action":"llm_reason","target":"llm","args":["Who are you?"],"project_id":"project_alpha","priority":"normal"}`).
3. Verify:
   - response is role-consistent
   - no role override from user text
   - traces/task ids are returned in governed response envelope

### 4.2 Mention-Driven Group Chat
1. In `#leadership_council`, send:
   - `/oq {"action":"llm_reason","target":"llm","args":["Summarize Project Alpha budget risk in 5 bullets."],"project_id":"project_alpha","priority":"normal"}`
   - mention `@CEO @Auditor` in the same message
2. Verify:
   - only `ceo` and `auditor` bots respond
   - no unmentioned role bot responds
   - response ordering/readability is deterministic enough for operator review
3. Send no-mention group command and verify fail-closed denial (`recipient_mentions_required`).

### 4.3 Long-Response Hardening
1. Ask for a long response (for example 20-bullet risk summary).
2. Verify:
   - multi-part chunked messages are emitted
   - no silent truncation
   - chunk labels are visible (`[role i/n]`)

### 4.4 Tool Governance Path
1. In DM with `@CEO`, send tool-read command:
   - `/oq {"action":"tool_read","target":"llm","args":["{\"tool\":\"get_project_lifecycle_state\",\"arguments\":{\"project_id\":\"project_alpha\"}}"],"project_id":"project_alpha","priority":"normal"}`
2. Verify:
   - response includes governed tool result with source citation tags
   - response role label matches `ceo`
3. In DM with `@ProjectManager`, send disallowed read-tool command:
   - `/oq {"action":"tool_read","target":"llm","args":["{\"tool\":\"get_audit_event_stream\",\"arguments\":{\"project_id\":\"project_alpha\"}}"],"project_id":"project_alpha","priority":"normal"}`
4. Verify:
   - fail-closed denial (`tool_access_denied`)
5. Send raw mutation write command:
   - `/oq {"action":"tool_write","target":"llm","args":["{\"tool\":\"raw_sql_update\",\"arguments\":{\"project_id\":\"project_alpha\"}}"],"project_id":"project_alpha","priority":"normal"}`
6. Verify:
   - fail-closed denial (`tool_raw_db_mutation_denied`)

## 5. Evidence Artifacts

Recommended command sequence:
- `uv run python ops/scripts/run_m10_live_multi_bot_acceptance.py --mode preflight`
- `uv run python ops/scripts/run_m10_live_multi_bot_acceptance.py --mode init-manifest --project-id <project_id>`
- `uv run python ops/scripts/run_m10_live_multi_bot_acceptance.py --mode init-notes --project-id <project_id>`
- `uv run python ops/scripts/check_m10_live_acceptance_artifacts.py`

Required capture set:
- `docker compose ps` snapshot
- `api_app` and `discord_bot_worker` logs with traces
- Discord screenshots for DM matrix and mention-group scenario
- Denial screenshot/log for no-mention group command
- Notes file with command payloads and observed trace/task IDs

Output targets:
- `implementation/v1/planning/artifacts/m10_live_preflight_latest.json`
- `implementation/v1/planning/artifacts/m10_live_acceptance_notes.md`
- `implementation/v1/planning/artifacts/m10_live_discord_worker_logs_latest.txt`
- `implementation/v1/planning/artifacts/m10_live_api_app_logs_latest.txt`
- `implementation/v1/planning/artifacts/m10_live_docker_compose_ps_latest.txt`
- `implementation/v1/planning/artifacts/m10_live_scenarios_manifest_latest.json`

## 6. Exit Criteria Mapping

- DM to each role bot is validated with role-consistent governed response.
- Mention-group scenario is validated for explicit-role fan-out only.
- Long-response chunking behavior is validated with no silent truncation.
- Tool-read/tool-write governance behavior is validated for allow + deny paths.
- Evidence artifacts are attached for M10 closeout.
