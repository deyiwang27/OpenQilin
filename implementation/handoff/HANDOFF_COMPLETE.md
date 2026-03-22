# Handoff Complete: M16-WP4 — Doctor / Diagnostics CLI

**Completed by:** CodeX (engineer)
**Date:** 2026-03-22
**Branch:** `feat/149-m16-wp4-doctor-cli`
**Draft PR:** N/A (not opened in this environment)
**Implements:** `implementation/handoff/current.md`

---

## Summary

Implemented a new synchronous infrastructure diagnostics layer in `shared_kernel/doctor.py` with pass/warn/fail reporting and fail-closed blocking startup checks for PostgreSQL, Redis, and OPA. Added a standalone operator CLI at `openqilin.apps.oq_doctor`, wired startup validation in `create_control_plane_app()`, and added a Docker Compose `oq_doctor` service profile. Added 16 unit tests for doctor behavior and updated the existing runtime entrypoint unit test to patch the new startup-check hook.

---

## Completed Tasks

| Task | Status | Notes |
|---|---|---|
| Implement `src/openqilin/shared_kernel/doctor.py` (`SystemDoctor`, `DoctorReport`, `DoctorCheck`, `run_blocking_startup_checks`) | ✅ Done | Implemented all required checks and check ordering. `agent_registry` is skipped with `warn` when PostgreSQL check fails. |
| Implement `src/openqilin/apps/oq_doctor.py` standalone CLI | ✅ Done | Added table-style output and exit code `1` on any `fail`, `0` otherwise. |
| Add `oq_doctor` service in `compose.yml` under `profiles: ["doctor"]` | ✅ Done | Added service with required environment and compose command `python -m openqilin.apps.oq_doctor`. |
| Replace `verify_opa_bundle_loaded` startup call with `run_blocking_startup_checks(settings)` in control-plane app | ✅ Done | `create_control_plane_app()` now invokes the doctor startup guard after connector-secret validation. |
| Add unit tests in `tests/unit/test_m16_wp4_doctor.py` | ✅ Done | Added all 16 required tests from handoff acceptance list. |
| Keep existing tests green after import/call-site swap | ✅ Done | Updated `tests/unit/test_m7_wp4_runtime_entrypoints.py` patch target to `run_blocking_startup_checks`. |

---

## Validation Results

```
InMemory gate:   PASS (project files; .venv excluded)
ruff check:      PASS
ruff format:     PASS
mypy:            PASS
pytest unit:     PASS (769 passed, 0 failed)
pytest component: PASS (included in combined run above)
```

Executed commands:
- `grep -r --include="*.py" -l "class InMemory" . | grep -v "/testing/" | grep -v "tests/" | grep -v "/.venv/"`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run python -m mypy .`
- `uv run python -m pytest tests/unit tests/component -x --tb=short -q` → `769 passed, 1 warning`

---

## REVIEW_NOTEs for Architect

| File | Line | Note |
|---|---|---|
| _None_ | - | No REVIEW_NOTEs added. |

---

## Spec Change Requests

| Conflict | Docs involved | Blocking question |
|---|---|---|
| _None_ | - | - |

---

## What Was Skipped

- Draft PR creation was not performed in this environment.

---

## Notes

- `uv run mypy .` and `uv run pytest ...` binaries were unavailable in this environment (`No such file or directory`), so equivalent module invocations were used (`uv run python -m mypy ...` and `uv run python -m pytest ...`).
