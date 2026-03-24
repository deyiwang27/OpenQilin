# Handoff Complete: M18-WP2 — @everyone Broadcast

**Completed by:** CodeX (engineer)
**Date:** 2026-03-23
**Branch:** `feat/196-m18-wp2-everyone-broadcast`
**Draft PR:** #197
**Implements:** `implementation/handoff/current.md`

---

## Summary

Implemented the M18-WP2 `@everyone` broadcast path end-to-end. The Discord bot worker now detects `message.mention_everyone`, forwards one request per bot process, the ingress schema carries `is_everyone_mention`, and the control plane routes each request directly to that bot's own advisory handler without cross-bot coordination.

---

## Completed Tasks

| Task | Status | Notes |
|---|---|---|
| Add `is_everyone_mention` to `DiscordInboundEvent` | ✅ Done | Added field with default `False` and populated it from `message.mention_everyone` |
| Update bot-worker free-text gate for `@everyone` | ✅ Done | Secretary no longer yields on `@everyone`; non-Secretary bots forward even when not individually listed in `message.mentions` |
| Add `is_everyone_mention` to `DiscordIngressRequest` | ✅ Done | Schema default is `False`; acceptance one-liner confirmed field construction works |
| Pass `is_everyone_mention` through `build_discord_ingress_payload()` | ✅ Done | Fan-in payload now includes the flag for control-plane routing |
| Add ingress `@everyone` fast-path advisory routing | ✅ Done | Non-Secretary bots route directly to their own advisory handler; Secretary falls through to its existing advisory block |
| Add unit tests for worker gate, ingress fast-path, and payload passthrough | ✅ Done | Added `tests/unit/test_m18_wp2_everyone_broadcast.py` with 8 focused cases |
| Update planning/progress docs | ✅ Done | M18-WP2 tasks/criteria checked and `ImplementationProgress-v2.md` marked `done` |

---

## Validation Results

```text
InMemory gate:    PASS
ruff check:       PASS
ruff format:      PASS
mypy:             PASS
pytest unit:      PASS  (880 passed, 1 warning in combined unit+component run)
pytest component: PASS  (880 passed, 1 warning in combined unit+component run)
```

---

## REVIEW_NOTEs for Architect

None.

---

## Spec Change Requests

None.

---

## What Was Skipped

None.

---

## Notes

- Draft PR opened: `#197`
- `implementation/handoff/current.md` had a pre-existing local modification and was intentionally left untouched.
