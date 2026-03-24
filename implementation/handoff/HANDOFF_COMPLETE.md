# Handoff Complete: M18-WP5 — Deterministic Advisory Topic Router

**Completed by:** CodeX (engineer)
**Date:** 2026-03-24
**Branch:** `feat/207-m18-wp5-advisory-topic-router`
**Draft PR:** #208
**Implements:** `implementation/handoff/current.md`

---

## Summary

Implemented the M18-WP5 Tier 1 deterministic advisory router and Redis-backed bot mention lookup. The control plane now intercepts unambiguous advisory topics before Secretary LLM routing, enforces project-channel restrictions for Auditor and Administrator referrals, and the Discord worker registers live bot user IDs in Redis on startup.

---

## Completed Tasks

| Task | Status | Notes |
|---|---|---|
| Add advisory routing helpers under `src/openqilin/control_plane/advisory/` | ✅ Done | Added `topic_router.py`, `channel_availability.py`, `bot_registry_reader.py`, and package marker |
| Wire `AdvisoryTopicRouter` and `BotRegistryReader` into `RuntimeServices` and dependency getters | ✅ Done | Added fields, construction, and FastAPI dependency accessors in `dependencies.py` |
| Insert Tier 1 deterministic advisory intercept into Secretary free-text ingress path | ✅ Done | Added direct role dispatch, fail-closed project-channel restriction checks, and referral messaging with optional bot mention |
| Register each bot's live Discord user ID in Redis on worker startup | ✅ Done | `discord_bot_worker.py` now builds one Redis client, passes it to each client, and writes `openqilin:bot_discord_ids` in `on_ready()` |
| Add unit coverage for topic routing, channel availability, bot registry reads, and Tier 1 ingress behavior | ✅ Done | Added 30 new unit tests plus component fixture updates for expanded `RuntimeServices` |
| Run acceptance validation and fix regressions | ✅ Done | Adjusted direct-call dependency fallback in `discord_ingress.py`; all requested checks now pass with one noted `uv run` tool quirk |

---

## Validation Results

```text
InMemory gate:     PASS
ruff check:        PASS
ruff format:       PASS
mypy:              PASS
pytest unit:       PASS  (included in combined run; total 914 passed, 0 failed)
pytest component:  PASS  (included in combined run; total 914 passed, 0 failed)
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

Nothing from the handoff scope was skipped.

---

## Notes

- The literal InMemory grep gate only passes when the repo-local virtualenv is moved outside the repo root because the command recursively scans third-party site-packages under `.venv/`; project source itself is clean.
- `uv run mypy .` and `uv run pytest tests/unit tests/component -x` failed to spawn the script entrypoints under local `uv 0.10.9`, so validation used the equivalent repo-venv commands `uv run python -m mypy .` and `uv run python -m pytest tests/unit tests/component -x`.
