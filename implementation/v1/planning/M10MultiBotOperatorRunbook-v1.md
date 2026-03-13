# M10 Multi-Bot Discord Operator Runbook

Date: `2026-03-13`  
Scope: `M10-WP6` multi-bot operations

## 1. Runtime Configuration

Required env settings:
- `OPENQILIN_DISCORD_MULTI_BOT_ENABLED=true`
- `OPENQILIN_DISCORD_ROLE_BOT_TOKENS_JSON`:
  - JSON object keyed by role (`administrator`, `auditor`, `ceo`, `cwo`, `project_manager`)
  - each entry may be string token or rich object:
    - `token`
    - `bot_id`
    - `guild_allowlist` (optional)
    - `status` (`active|disabled`)
- `OPENQILIN_DISCORD_REQUIRED_ROLE_BOTS_CSV`
- `OPENQILIN_DISCORD_CONTROL_PLANE_BASE_URL`
- `OPENQILIN_CONNECTOR_SHARED_SECRET`

Delivery hardening knobs:
- `OPENQILIN_DISCORD_RESPONSE_CHUNK_SIZE_CHARS`
- `OPENQILIN_DISCORD_RESPONSE_RETRY_ATTEMPTS`
- `OPENQILIN_DISCORD_RESPONSE_RETRY_BASE_DELAY_SECONDS`

## 2. Startup Validation

Fail-closed startup checks:
- required role-bot mappings must exist and be active
- duplicate tokens are rejected
- duplicate `bot_id` values are rejected
- invalid registry JSON is rejected

Runtime readiness:
- readiness marker `/tmp/openqilin.discord_bot_worker.ready` is present only when all required role bots are online
- marker is removed if a required role bot disconnects

## 3. Recipient Routing Semantics

DM:
- recipient is fixed to target role bot identity (`bot_id`, `bot_role`)

Group chat:
- recipients are resolved from explicit role-bot mentions only
- no mention => fail-closed deny (`recipient_mentions_required`)
- mismatch between payload recipients and resolved mentions => deny (`recipient_mismatch`)

## 4. Outbound Delivery Behavior

- long replies are chunked into multi-part messages
- chunk labels are prefixed for readability (`[role i/n]`)
- transient outbound send failures (`429`, `5xx`) retry with bounded backoff
- best-effort role ordering is applied for same-message multi-bot responses

## 5. Incident Response

### 5.1 Frequent `429` provider errors
1. Reduce traffic burst / increase spacing between commands.
2. Verify provider model settings and fallback model health.
3. Inspect `api_app` logs for `llm_provider_unavailable` traces.

### 5.2 Missing role bot responses
1. Confirm role bot is online in Discord member list.
2. Check worker logs for disconnect/readiness warnings.
3. Verify token registry entry for that role is `active` and non-empty.
4. Verify `OPENQILIN_DISCORD_REQUIRED_ROLE_BOTS_CSV` includes expected roles.

### 5.3 Truncated or fragmented responses
1. Check chunk-size and retry env settings.
2. Confirm chunk labels are present in outbound channel.
3. Collect worker logs and affected trace/task IDs for investigation.

## 6. Evidence Capture

When reporting runtime incidents, include:
- `docker compose ps`
- `docker compose logs discord_bot_worker --tail=400`
- `docker compose logs api_app --tail=400`
- command payload used and returned trace/task IDs
- screenshots for DM/group behavior where relevant
