# Handoff Complete: M18-WP1 — Conversational Advisory Mode for Institutional Agents

**Completed by:** CodeX (engineer)
**Date:** 2026-03-23
**Branch:** `feat/193-m18-wp1-conversational-advisory`
**Draft PR:** #194
**Implements:** `implementation/handoff/current.md`

---

## Summary

Implemented conversational free-text advisory for CEO, CWO, CSO, Auditor, Administrator, and Project Manager; replaced the bot-worker canned intro/DM blocking path with control-plane forwarding; and generalized the Discord ingress advisory bypass to dispatch to all six agents. Added conversation-history persistence guards, advisory metric emission, role-specific prompts, and 24 unit tests covering the new handler paths.

---

## Completed Tasks

| Task | Status | Notes |
|---|---|---|
| Secretary prompt update for new-project routing | ✅ Done | `ADVISORY_SYSTEM_PROMPT` now routes new-project initiation to CWO and preserves PM routing for approved/active work |
| Bot-worker free-text forwarding fixes | ✅ Done | Removed the canned intro path and relaxed the non-Secretary DM block so free-text reaches the control plane |
| Shared advisory request/response models | ✅ Done | Added `FreeTextAdvisoryRequest` and `FreeTextAdvisoryResponse` under `src/openqilin/agents/shared/` |
| Six agent `handle_free_text()` implementations | ✅ Done | Added role-specific conversational prompts, fallbacks, history load/store, and advisory responses for CEO/CWO/CSO/Auditor/Administrator/PM |
| Advisory metrics and DI wiring | ✅ Done | Wired `conversation_store` into all six agents and `llm_gateway`/`metric_recorder` into Auditor and Administrator; also fixed missing metric wiring for Secretary and PM |
| Discord ingress six-agent advisory bypass | ✅ Done | Added per-bot-role advisory dispatch with auth validation and broad fallback handling |
| Unit coverage for conversational advisory | ✅ Done | Added 24 unit tests across six new files under `tests/unit/agents/` |
| Planning/progress updates | ✅ Done | Ticked the M18-WP1 checklist items and marked M18-WP1 `done` in `ImplementationProgress-v2.md` |

---

## Validation Results

```text
InMemory gate:    PASS
ruff check:       PASS
ruff format:      PASS
mypy:             PASS
pytest unit:      PASS  (872 passed, 1 warning in combined unit+component run)
pytest component: PASS  (872 passed, 1 warning in combined unit+component run)
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

- `uv run pytest` and `uv run mypy` were not available as direct entrypoints in this shell, so validation used `uv run python -m pytest ...` and `uv run python -m mypy .`.
- `implementation/handoff/current.md` and `implementation/v2/planning/05-milestones/M17-WorkPackages-v1.md` had pre-existing local modifications and were intentionally left untouched.
