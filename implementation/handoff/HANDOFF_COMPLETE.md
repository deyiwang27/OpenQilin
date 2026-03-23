# Handoff Complete: M17-WP8 — Conversation Memory Foundation

**Completed by:** CodeX (engineer)
**Date:** 2026-03-23
**Branch:** `feat/179-m17-wp8-conversation-memory-foundation`
**Draft PR:** TBD
**Implements:** `implementation/handoff/current.md`

---

## Summary

Implemented the M17-WP8 conversation memory foundation end-to-end: unified per-channel scope, hot window increase to 40 rows, warm window summary persistence, and Secretary scope alignment. Added the required migrations, extended conversation store interfaces/implementations, updated dispatch prompt composition to include warm summaries, and added the full WP8 unit test matrix. All required validation gates passed.

---

## Completed Tasks

| Task | Status | Notes |
|---|---|---|
| Add `ConversationMemoryConfig` dataclass | ✅ Done | Added to `src/openqilin/shared_kernel/config.py` before `RuntimeSettings` |
| Add migration `20260323_0015` for `conversation_windows` | ✅ Done | New table + scope index |
| Add migration `20260323_0016` for `agent_id` / `window_index` columns | ✅ Done | Extended `conversation_messages` via Alembic |
| Replace `PostgresConversationStore` with windowed warm-tier implementation | ✅ Done | Added `max_turns=40`, `window_size`, `summarize_fn`, `list_windows()`, `fetch_window()`, window close behavior |
| Update `llm_dispatch` scope/prompt/store protocol/local store | ✅ Done | Unified scope format, warm summary dataclass/methods, prompt warm block, `append_turns(..., agent_id=...)`, local fallback 40 |
| Add `guild_id` to `SecretaryRequest` and unify Secretary scope | ✅ Done | Updated models, agent scope construction, and ingress wiring |
| Update existing affected tests | ✅ Done | Updated scope/prompt expectations in M16/M11/M2 test files |
| Add new WP8 unit test file | ✅ Done | Added `tests/unit/test_m17_wp8_conversation_memory_foundation.py` with all required cases |
| Run acceptance validation matrix | ✅ Done | All specified gates passed (with noted command-form equivalence) |

---

## Validation Results

```
InMemory gate:    PASS
ruff check:       PASS
ruff format:      PASS
mypy:             PASS
pytest unit:      PASS  (829 passed, 1 warning; run combined with component as requested)
pytest component: PASS  (run as combined suite)
```

Additional acceptance verifications:
- Unified scope assertion script: PASS (`scope ok: guild::guild_1::channel::channel_1`)
- `SecretaryRequest.guild_id` default/set assertion script: PASS
- `LocalConversationStore` max turns assertion script: PASS

Environment command notes:
- `uv run pytest ...` entrypoint is unavailable in this environment, so equivalent command was used: `uv run python -m pytest ...`.
- `uv run mypy .` entrypoint is unavailable in this environment, so equivalent command was used: `uv run python -m mypy .`.

---

## REVIEW_NOTEs for Architect

| File | Line | Note |
|---|---|---|
| — | — | No `REVIEW_NOTE` comments were added |

---

## Spec Change Requests

| Conflict | Docs involved | Blocking question |
|---|---|---|
| — | — | — |

---

## What Was Skipped

- Draft PR creation was not performed in this execution context.

---

## Notes

- To ensure runtime hot-window behavior aligns with WP intent (40 rows) when persistence is enabled, `src/openqilin/control_plane/api/dependencies.py` conversation-store wiring was updated from `max_turns=6` to `max_turns=40`.
- The acceptance snippet in `current.md` for `SecretaryRequest` omitted required constructor args (`context`, `trace_id`); an equivalent check with those required args was executed and passed.
- After WP8 delivery, the branch also picked up follow-up M17-WP6 sponsorship repo updates so Claude review is aware of them: GitHub funding config was corrected to `.github/FUNDING.yml`, README gained a sponsor badge/link, and sponsorship status/docs were refreshed to reflect the now-active GitHub Sponsors profile.
