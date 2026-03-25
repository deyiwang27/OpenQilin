# Handoff Complete: Topic Router + Mention Detection Fixes

**Completed by:** CodeX (engineer)
**Date:** 2026-03-24
**Branch:** `fix/topic-router-and-mention-detection`
**Draft PR:** #222
**Implements:** explicit user-requested bugfixes

---

## Summary

Added the missing `administrator` Tier 1 keywords so infrastructure and policy-health prompts route deterministically without falling through to Secretary's LLM. Expanded the remaining advisory keyword sets across `auditor`, `cso`, `project_manager`, `cwo`, and `ceo`, and kept the Secretary mention-gate Redis fix in place. Added unit coverage for the new routing terms and re-ran the requested validation matrix.

---

## Completed Tasks

| Task | Status | Notes |
|---|---|---|
| Add `administrator` entry to `TOPIC_ROUTING_TABLE` | ✅ Done | Added the requested keyword set in `src/openqilin/control_plane/advisory/topic_router.py` |
| Fix Secretary bot-mention detection without Discord members intent | ✅ Done | `src/openqilin/apps/discord_bot_worker.py` now unions mention IDs from `message.mentions` with the Redis bot registry |
| Add regression tests for Administrator routing | ✅ Done | Added coverage in `tests/unit/advisory/test_topic_router.py` |
| Expand advisory keyword coverage for other institutional agents | ✅ Done | Added the requested keywords to `auditor`, `cso`, `project_manager`, `cwo`, and `ceo` in `src/openqilin/control_plane/advisory/topic_router.py` |
| Add regression tests for newly added agent keywords | ✅ Done | Added one unit test per requested agent keyword in `tests/unit/advisory/test_topic_router.py` |
| Add regression test for Secretary skipping when a registry-known bot is @mentioned | ✅ Done | Added coverage in `tests/unit/test_discord_bot_worker_tier1_absent.py` |
| Run requested validation matrix | ✅ Done | Governance grep, Ruff, mypy, and `uv run pytest tests/unit tests/component -x` all passed after the keyword expansion |

---

## Validation Results

```text
InMemory gate:    PASS
ruff check:       PASS
ruff format:      PASS
mypy:             PASS
pytest unit:      PASS  (run in combined command)
pytest component: PASS  (run in combined command; total result 946 passed, 0 failed)
```

---

## REVIEW_NOTEs for Architect

None.

---

## Spec Change Requests

| Conflict | Docs involved | Blocking question |
|---|---|---|
| `implementation/handoff/current.md` currently describes unrelated DeepSeek provider work while this branch implements the explicit terminal-requested bugfixes above. | `implementation/handoff/current.md` vs terminal task request | Should `current.md` be refreshed before the next engineer handoff to avoid task/branch mismatch? |

---

## What Was Skipped

Nothing was skipped from the explicit requested scope.

---

## Notes

`implementation/handoff/current.md` had pre-existing local modifications in the worktree and was left untouched. Unrelated uncommitted paths present before this work, including `memory/`, were also left untouched. One existing component test fixture was updated from `"Send status update to ceo."` to `"Send update to ceo."` because the newly requested `project_manager` keyword `status` now correctly triggers Tier 1 advisory routing.
