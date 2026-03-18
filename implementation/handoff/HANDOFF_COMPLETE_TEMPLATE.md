# Handoff Complete: <Task-ID> — <Short Title>

**Completed by:** CodeX (engineer)
**Date:** <date>
**Branch:** `<branch-name>`
**Draft PR:** #<pr-number>
**Implements:** `implementation/handoff/current.md`

---

## Summary

<!-- 2-3 sentences: what was built and whether it matches the handoff doc -->

---

## Completed Tasks

<!-- List each task from the handoff doc with status -->

| Task | Status | Notes |
|---|---|---|
| <description> | ✅ Done / ⚠️ Partial / ❌ Skipped | <reason if not Done> |

---

## Validation Results

```
InMemory gate:   PASS / FAIL
ruff check:      PASS / FAIL
ruff format:     PASS / FAIL
mypy:            PASS / FAIL
pytest unit:     PASS / FAIL  (<N> passed, <N> failed)
pytest component: PASS / FAIL
```

---

## REVIEW_NOTEs for Architect

<!-- One entry per REVIEW_NOTE left in the code. -->
<!-- The Architect resolves these — do not leave them in production code permanently. -->

| File | Line | Note |
|---|---|---|
| `src/openqilin/.../foo.py` | 42 | <what the ambiguity is and what conservative choice was made> |

---

## Spec Change Requests

<!-- Fill in if any spec conflict or gap was discovered that could not be resolved conservatively. -->
<!-- Leave blank if none. -->

| Conflict | Docs involved | Blocking question |
|---|---|---|
| <describe the conflict> | `spec/...` vs `design/...` | <what decision is needed> |

---

## What Was Skipped

<!-- Anything from the handoff "Out of Scope" that was accidentally approached, or any task that -->
<!-- could not be completed. Explain why. -->

---

## Notes

<!-- Anything else the Architect should know before reviewing the PR. -->
