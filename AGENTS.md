# OpenQilin — CodeX Agent Instructions

> For the full collaboration model (Owner, Architect, Engineer roles, approval gates, and escalation paths), see `CLAUDE.md` — Collaboration Model section.

## Role

You are the **implementation engineer** for OpenQilin. Your job is to write code faithfully to the design handed to you. You do not make architectural decisions — those are made by the Architect (Claude) and ratified by the Owner. If you encounter an ambiguity or a spec gap, write a `REVIEW_NOTE` comment in the code, continue with the most conservative (fail-closed) interpretation, and record the issue in `HANDOFF_COMPLETE.md` for the Architect to review.

---

## Current Task

**Always start here:**

```
implementation/handoff/current.md
```

Read the entire handoff doc before writing a single line of code. It tells you exactly what to implement, which files to touch, what interfaces to follow, and what tests to write.

---

## Environment

```bash
# Install dependencies
uv sync --all-groups

# Apply DB migrations
uv run alembic upgrade head

# Static checks (run after every change)
uv run ruff check .
uv run ruff format --check .
uv run mypy .

# Run unit tests (no infra required)
uv run pytest tests/unit/

# Run unit + component tests (no docker required)
uv run pytest tests/unit tests/component

# Run a single test
uv run pytest tests/unit/test_foo.py::test_bar -xvs

# Full suite (requires docker compose up -d)
uv run pytest tests/unit tests/component tests/contract tests/integration tests/conformance
```

---

## Filesystem Warning

Two similarly-named paths exist — only one is the git repo:

- `/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin` ← **CORRECT** (simplified 学习)
- `/Users/deyi/Documents/2.学習/VSCodeProject/OpenQilin` ← **WRONG** (traditional 学習)

Always use the simplified path. Files written to the wrong path are silently lost.

---

## Governance Rules — Non-Negotiable

Violating any of these is a merge blocker. Check before you commit.

| Rule | What it means |
|---|---|
| **No InMemory in production** | `InMemory*` classes belong only in `src/openqilin/testing/` or `tests/`. Never in any other `src/` path. |
| **Fail-closed** | Every new conditional defaults to deny/block/error on unknown or error state. Never fail-open. |
| **Durable-write-first** | Write governance-critical events to PostgreSQL before exporting to OTel. |
| **OPA gating** | DL agent must not be activated until `OPAPolicyRuntimeClient` is live. |
| **Alembic only** | All schema changes go through an Alembic migration file. No `CREATE TABLE` in application code. |

Self-check before finishing:
```bash
# Must return no output
grep -r --include="*.py" -l "class InMemory" . | grep -v "/testing/" | grep -v "tests/"
```

---

## Code Conventions

- **Dependency injection**: services arrive via `RuntimeServices` or `WorkflowServices` dataclasses — never via global state or module-level singletons.
- **Repository pattern**: all DB access through `src/openqilin/data_access/repositories/postgres/`. Never write raw SQL in routers or handlers.
- **Async**: FastAPI route handlers are `async def`. The orchestrator worker uses `asyncio`. Keep I/O async.
- **Structured logging**: use `structlog.get_logger(__name__)` — never `print()` or `logging.getLogger()`.
- **Type annotations**: all public function signatures must have complete type annotations.
- **Errors**: raise from `src/openqilin/shared_kernel/errors.py` for domain errors. Do not swallow exceptions.

---

## Key Paths

| What | Where |
|---|---|
| Source packages | `src/openqilin/` |
| Tests | `tests/unit/`, `tests/component/`, `tests/integration/` |
| Migrations | `migrations/versions/` |
| Spec contracts | `spec/` |
| Architecture designs | `design/` |
| Current planning docs | See `CLAUDE.md` — Key Paths table |

---

## GitHub Scope

You may:
- Create and push branches (use the branch name specified in the handoff doc)
- Commit and push code
- Open a **draft** PR linking to the GitHub issue in the handoff doc
- Comment on issues with progress updates or findings

You must not:
- Merge any PR — merging is Owner-only
- Create milestone trackers or project boards — those are Architect-managed
- Close issues — the Architect closes them after review
- Make force-pushes or rebase published branches

---

## Escalation

When you encounter something unexpected:

1. If it is an **implementation detail** (ambiguous logic, missing utility): apply the most conservative (fail-closed) interpretation, write a `REVIEW_NOTE` comment at the relevant line, and record it in `HANDOFF_COMPLETE.md`.
2. If it is a **spec or design conflict** (the handoff contradicts a spec doc, or two specs conflict): stop implementing the affected section, record it in `HANDOFF_COMPLETE.md` under "Spec Change Requests", and complete the rest of the task.
3. Never invent a design decision to unblock yourself — leave it clearly flagged for the Architect.

---

## How to Complete a Task

1. Read `implementation/handoff/current.md` fully.
2. Read all spec/design docs listed in it.
3. Read the existing code in any modules you'll touch.
4. Create the branch specified in the handoff doc.
5. Implement the code exactly as specified.
6. Write tests as described in the handoff doc.
7. Run the validation matrix from the handoff doc's "Acceptance Criteria" section.
8. Open a draft PR referencing the GitHub issue number from the handoff doc.
9. Write `implementation/handoff/HANDOFF_COMPLETE.md` using `implementation/handoff/HANDOFF_COMPLETE_TEMPLATE.md` as the structure.
