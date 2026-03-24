# Handoff Complete: Fix #209 — Tier 1 Advisory Bot Routing

**Completed by:** CodeX (engineer)
**Date:** 2026-03-24
**Branch:** `fix/209-tier1-bot-routing`
**Draft PR:** #210
**Implements:** `implementation/handoff/current.md`

---

## Summary

Implemented the issue #209 follow-up to M18-WP5 so Tier 1 advisory free-text is forwarded by, and answered through, the matched advisory bot instead of always posting through Secretary. The Discord bot worker now pre-routes non-command free-text to the Tier 1 target bot, the ingress router dispatches Tier-1-forwarded advisory messages directly to that agent, and regression coverage was added for both worker and ingress behavior.

---

## Completed Tasks

| Task | Status | Notes |
|---|---|---|
| Add Tier 1 pre-routing to `discord_bot_worker.py` free-text gate | ✅ Done | Instantiated `AdvisoryTopicRouter`, routed only the matched target bot through, and preserved Secretary fallback for no-match and project-channel restricted roles |
| Preserve Tier 1 target through the later worker recipient gate | ✅ Done | Required so runtime-placeholder recipients do not cause the matched non-Secretary bot to return early before forwarding |
| Add Tier-1-forwarded advisory dispatch path to `discord_ingress.py` | ✅ Done | Non-Secretary advisory bots that forward free-text with resolved Secretary intent now call their own `handle_free_text()` directly |
| Add regression tests for worker routing and ingress forwarding | ✅ Done | Added worker coverage for auditor targeting, Secretary skip, project restriction fallback, no-match fallback, and ingress forwarded-auditor dispatch |
| Run requested validation matrix | ✅ Done | All requested commands now pass locally |

---

## Validation Results

```text
InMemory gate:     PASS
ruff check:        PASS
ruff format:       PASS
mypy:              PASS
pytest unit:       PASS
pytest component:  PASS
```

---

## REVIEW_NOTEs for Architect

None.

---

## Spec Change Requests

| Conflict | Docs involved | Blocking question |
|---|---|---|

---

## What Was Skipped

Nothing from the requested issue scope was skipped.

---

## Notes

- The worker fix needed one additional guard adjustment beyond the issue summary: after recipient resolution, non-Secretary bots were still returning early when the recipient tuple remained the runtime placeholder. The final implementation preserves the Tier 1 target through that later gate so the matched bot actually forwards.
- Local validation wrappers were repaired so the literal requested commands pass:
  - `.venv` is now a symlink to an external venv path, which keeps the governance grep from recursing into third-party site-packages.
  - The `pytest` and `mypy` console-script shebangs in `.venv/bin/` were updated from a stale old repo path to the current repo path so `uv run pytest ...` and `uv run mypy .` execute correctly.
