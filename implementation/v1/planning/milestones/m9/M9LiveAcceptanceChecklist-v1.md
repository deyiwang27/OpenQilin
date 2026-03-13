# M9 Live Discord Acceptance Checklist

Date: `2026-03-12`  
Milestone: `M9 MVP Real Discord Runtime and Live Validation`  
Work package: `M9-WP3` (`#55`)

## 1. Goal

Execute real Discord end-to-end MVP validation on Docker `full` runtime and capture deterministic evidence for milestone closeout.

## 2. Preconditions

- Docker CLI and daemon available on operator machine.
- Discord bot token configured (`OPENQILIN_DISCORD_BOT_TOKEN`).
- Discord application privileged intents required by runtime are enabled in Developer Portal (at minimum Message Content Intent).
- Gemini API key configured (`OPENQILIN_GEMINI_API_KEY`) for LLM dispatch path validation.
- Connector secret is non-default for non-local validation (`OPENQILIN_CONNECTOR_SHARED_SECRET`).
- Discord guild/channels created and mapped for:
  - `leadership_council`
  - `governance`
  - `executive`
  - one project channel (`project-<project_id>`)

## 3. Runtime Boot

1. `docker compose --profile full up -d --build`
2. Verify health:
   - `api_app`, `orchestrator_worker`, `communication_worker`, `discord_bot_worker` all healthy.
3. Capture startup logs:
   - `docker compose logs api_app --tail=200`
   - `docker compose logs discord_bot_worker --tail=200`

## 4. Live Scenarios

## 4.1 Completed-to-Archived Branch
1. Submit proposal/governance commands from Discord through bot.
2. Drive lifecycle through:
   - `proposed -> approved -> active -> paused -> active -> completed -> archived`
3. Verify:
   - governed responses are posted back to Discord with trace/task correlation.
   - completed project channel is read-only.
   - archived project channel is locked.

## 4.2 Terminated-to-Archived Branch
1. Create second project via Discord-governed path.
2. Drive lifecycle through:
   - `proposed -> approved -> active -> terminated -> archived`
3. Verify:
   - invalid transition `completed -> terminated` is denied fail-closed.

## 5. Evidence Artifacts

Required capture set:
- Preflight report:
  - `python ops/scripts/run_m9_live_discord_acceptance.py --mode preflight`
- Notes template initialization:
  - `python ops/scripts/run_m9_live_discord_acceptance.py --mode init-notes --project-id <project_id>`
- Discord screenshots for each lifecycle phase and denial case.
- API + Discord worker logs with trace/correlation IDs.
- Command output snapshots:
  - `docker compose ps`
  - `docker compose logs api_app --tail=400`
  - `docker compose logs discord_bot_worker --tail=400`
- Generated manifest JSON from:
  - `python ops/scripts/run_m9_live_discord_acceptance.py --mode init-manifest`
- Artifact integrity check:
  - `python ops/scripts/check_m9_live_acceptance_artifacts.py`

Output targets:
- `implementation/v1/planning/artifacts/m9_live_preflight_latest.json`
- `implementation/v1/planning/artifacts/m9_live_acceptance_manifest_latest.json`
- `implementation/v1/planning/artifacts/m9_live_acceptance_notes.md` (operator notes + trace links)

## 6. Exit Criteria Mapping

- Real Discord bot receives and replies through governed runtime path.
- Discord-governed lifecycle scenarios execute end-to-end for both branches.
- Evidence artifacts are complete and reproducible for `M9-WP4` closeout pack.
