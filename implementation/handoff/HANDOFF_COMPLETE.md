# Handoff Complete: M14-WP7 — File-Backed Artifact Storage

**Completed by:** CodeX (engineer)
**Date:** 2026-03-18
**Branch:** `feat/118-m14-wp7-file-backed-storage`
**Draft PR:** #119
**Implements:** `implementation/handoff/current.md`

---

## Summary

Implemented canonical file-backed artifact storage under `OPENQILIN_SYSTEM_ROOT/projects/...`, wired it into the Postgres governance artifact repository, and added administrator-side file/hash verification with immutable audit events on failure. Runtime dependency wiring, component test wiring, environment documentation, and the WP7 unit coverage were updated to match the handoff.

---

## Completed Tasks

| Task | Status | Notes |
|---|---|---|
| Add `ArtifactFileStore` in `src/openqilin/data_access/artifact_file_store.py` | ✅ Done | Added canonical write/read path, SHA-256 hashing, and path-traversal guards |
| Extend `PostgresGovernanceArtifactRepository` to use file-backed writes when configured | ✅ Done | Falls back to existing `db://` URI path when no file store is injected |
| Extend `DocumentPolicyEnforcer` with `verify_storage_uri_hash()` | ✅ Done | Emits immutable audit events on read failure or hash mismatch |
| Wire `ArtifactFileStore` into `RuntimeServices` and `build_runtime_services()` | ✅ Done | Runtime container now constructs and passes one shared file store |
| Update component test runtime wiring | ✅ Done | `tests/component/conftest.py` now builds and injects a temp-root file store |
| Document `OPENQILIN_SYSTEM_ROOT` in `.env.example` | ✅ Done | Added the M14-WP7 env block |
| Add WP7 unit tests | ✅ Done | Added 10 tests for writes, reads, traversal guard, and integrity verification |

---

## Validation Results

```
InMemory gate:   PASS
ruff check:      PASS
ruff format:     PASS
mypy:            PASS
pytest unit:     PASS  (627 passed, 0 failed)
pytest component: PASS  (66 passed, 0 failed)
```

---

## REVIEW_NOTEs for Architect

| File | Line | Note |
|---|---|---|

---

## Spec Change Requests

| Conflict | Docs involved | Blocking question |
|---|---|---|

---

## What Was Skipped

Nothing.

---

## Notes

- The literal grep command from the handoff began matching third-party packages under `.venv/` after dependency sync, so the production-code gate was executed with `--exclude-dir='.venv'`.
- `uv run pytest ...` and `uv run mypy .` failed because the local venv wrapper scripts have stale shebangs; validation was executed successfully via `uv run python -m pytest ...` and `uv run python -m mypy .`.
