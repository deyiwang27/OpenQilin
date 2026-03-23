# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# OpenQilin — Claude Code Context

## Project

OpenQilin is a governed, multi-agent AI assistant framework targeting solopreneur operators. Agents coordinate tasks through Discord; operators monitor via Grafana. The system enforces policy through OPA, persists state in PostgreSQL, and uses Redis for idempotency.

Current phase: **MVP-v2** — M13 active, M13-WP1 done, M13-WP9 pending (1 / 9 WPs done).

---

## Collaboration Model

Three roles, each with a distinct scope of authority:

| Role | Who | Responsibilities |
|---|---|---|
| **Owner** | Deyi | Proposes ideas; drafts initial spec/design; approves design revisions (Gate 1); approves WP plan (Gate 2); merges PRs to main |
| **Architect** | Claude | Reviews spec/design for flaws, conflicts, gaps; proposes revisions; breaks approved design into milestones and WPs; writes handoff docs; manages GitHub (issues, branches, PR creation); reviews CodeX artifacts; resolves minor findings; escalates spec changes to Owner; authors ADRs |
| **Engineer** | CodeX | Implements from handoff docs; creates branches, commits, pushes, opens draft PRs; writes HANDOFF_COMPLETE.md; flags issues as REVIEW_NOTEs |

### Workflow

```
Owner proposes idea
  → Owner drafts initial spec/design (Claude assists)
  → /design-review <doc>: Claude reviews for flaws, conflicts, gaps, proposes revisions
  → Owner approves revised design                          ← Gate 1
  → Claude writes milestones + WPs, creates GitHub milestone tracker
  → Owner approves WP plan                                 ← Gate 2
  → /architect <WP-ID>: Claude writes handoff, creates GitHub issue, creates branch
  → codex "Read CLAUDE.md and AGENTS.md, then implement implementation/handoff/current.md"
  → CodeX: implements, opens draft PR, writes HANDOFF_COMPLETE.md
  → Claude: reads HANDOFF_COMPLETE.md, runs /validate + /spec-review + /governance-check
    → REVIEW_NOTE or minor gap → Claude resolves, documents in ADR if significant
    → Spec change needed → Claude updates spec, flags to Owner before requesting merge
  → Owner merges PR to main (squash)
  → Claude closes GitHub issue, runs /wp <ID> done, updates ImplementationProgress
```

### Review Gates

| Gate | Skill | When | Who unblocks |
|---|---|---|---|
| Gate 1 — Design | `/design-review` | After owner drafts spec/design, before WP breakdown | Owner approves revisions |
| Gate 2 — WP Plan | `/wp <M#> status` | After WP list is written, before implementation | Owner confirms scope |
| Post-impl — Alignment | `/spec-review` | After CodeX finishes, before merge | Claude resolves or escalates |
| Post-impl — Quality | `/validate` + `/governance-check` | After CodeX finishes, before merge | Claude resolves |

### GitHub Scope

| Action | Who |
|---|---|
| Create/update issues and milestone trackers | Claude |
| Create branch | Claude (in handoff) or CodeX |
| Commit, push | CodeX |
| Open draft PR | CodeX |
| Review PR, request changes | Claude |
| Merge PR to main | Owner only |
| Author ADRs | Claude |
| Ratify ADRs | Owner |

### Escalation

CodeX findings route through Claude first. Claude escalates to Owner only when:
- A spec or design doc needs changing
- A governance constraint must be relaxed
- A milestone scope change is required

Everything else Claude resolves independently and records in an ADR or inline comment.

### Fix Delegation Rule

**Claude must not make code commits or push directly — including for CI failures, test patches, config corrections, or spec-review defect fixes.**

When a defect is found (by CI, spec-review, or governance-check), the workflow is:

```
Claude: diagnose root cause precisely
  → write targeted fix description:
      - exact file(s) and line(s) to change
      - what to change and why
      - which tests to run to verify
  → invoke CodeX MCP:
      mcp__codex__codex(
          prompt="<fix description>",
          sandbox="danger-full-access",
          approval-policy="never",
      )
  → CodeX: makes the change, commits, pushes, updates the PR
  → Claude: reviews the result
```

This applies even for one-line fixes. The principle: Architect diagnoses; Engineer implements. Keeping this boundary ensures PR ownership stays with CodeX and the Owner can trace every code change to an engineer commit.

### Engineer Instructions

CodeX (implementation engineer) has a separate instruction file:
- **`AGENTS.md`** — role definition, GitHub scope, governance rules, escalation paths, environment setup, and task completion protocol.

All parties should read both `CLAUDE.md` and `AGENTS.md` to understand the full workflow.

### ADR Authoring Convention

Significant architectural decisions are recorded as ADRs in `design/v2/adr/`. Claude authors; Owner ratifies.

Use `design/v2/adr/ADR-TEMPLATE.md` as the structure. Numbering is sequential (check existing files for the next number). Status lifecycle: `Proposed → Approved → Superseded`.

---

## Code Architecture

### Runtime Process Model

Two long-running processes:

1. **Control Plane** (`src/openqilin/apps/control_plane_app.py`) — FastAPI app that receives Discord webhooks, authenticates callers, parses intent, and enqueues tasks to PostgreSQL. Exposed at `:8000`.
2. **Orchestrator Worker** (`src/openqilin/apps/orchestrator_worker.py`) — Async worker loop that drains the task queue through the LangGraph pipeline. No HTTP surface.

### Discord → Task Lifecycle

```
Discord message
  → control_plane/routers/discord_ingress.py   (HTTP ingress, idempotency check)
  → control_plane/grammar/                     (CommandParser → IntentClassifier → FreeTextRouter)
  → control_plane/handlers/                    (creates Task row in PostgreSQL, status=queued)
  → orchestrator_worker (polls queue)
  → task_orchestrator/workflow/graph.py        (LangGraph StateGraph)
        policy_evaluation_node                 (OPA: authorize or deny)
        → obligation_check_node                (constitution obligations)
        → budget_reservation_node              (budget approval)
        → dispatch_node                        (routes to agent)
  → agents/secretary/ or agents/cso/          (agent execution)
  → communication_gateway/                    (Discord reply via outcome notifier)
```

### Key Packages

| Package | Role |
|---|---|
| `control_plane/` | FastAPI app, routers, grammar parsing, identity, idempotency |
| `task_orchestrator/` | LangGraph pipeline, state machine, loop cap enforcement |
| `agents/secretary/` | Secretary agent (Discord task routing) |
| `agents/cso/` | CSO agent (portfolio advice; does not use OPA) |
| `data_access/` | PostgreSQL repositories, Redis cache, SQLAlchemy engine |
| `policy_runtime_integration/` | OPA client (`OPAPolicyRuntimeClient`) — must be live before DL agent |
| `project_spaces/` | Project↔Discord channel bindings, routing resolver |
| `budget_runtime/` | Budget reservation and approval |
| `communication_gateway/` | Discord send/receive, outcome notifier |
| `observability/` | OTel tracing, audit writer, metrics |
| `shared_kernel/` | `RuntimeSettings`, error types, identifiers, startup validation |
| `testing/` | In-process stubs only (`InMemory*`) — never import from production code |

### Dependency Injection Pattern

`control_plane/api/dependencies.py` builds a `RuntimeServices` dataclass at startup. All routers and the orchestrator worker receive services through this container — never via global state. Component tests override this via the `patch_build_runtime_services` autouse fixture.

### LangGraph Task Graph

`task_orchestrator/workflow/graph.py` builds a `StateGraph(TaskState)`. Each node is a closure over `WorkflowServices` (a snapshot from `RuntimeServices`). Conditional edges implement fail-closed routing: any non-authorized/non-approved outcome exits to `END` without proceeding.

---

## Filesystem Path

The repository root is:

- `/Users/deyi/Documents/2.Learn/VSCodeProject/OpenQilin`

Always use this path when constructing absolute paths. The old Chinese-named directories (`2.学习`, `2.学習`) no longer exist.

---

## Key Paths

| What | Where |
|---|---|
| Master milestone plan | `implementation/v2/planning/05-milestones/MvpV2MilestonePlan-v1.md` |
| WP task lists | `implementation/v2/planning/05-milestones/M{11-17}-WorkPackages-v1.md` |
| Progress mirror | `implementation/v2/planning/ImplementationProgress-v2.md` |
| Bug backlog (20 findings) | `implementation/v2/planning/00-direction/ArchitecturalReviewFindings-v2.md` |
| Per-milestone module designs | `design/v2/architecture/M*-*ModuleDesign-v2.md` |
| Component deltas (v1→v2) | `design/v2/components/` |
| ADRs | `design/v2/adr/ADR-0004` through `ADR-0007` |
| Success criteria | `implementation/v2/planning/00-direction/MvpV2SuccessCriteria-v1.md` |
| Governance check | `implementation/v2/workflow/RepositoryConsistencyAndGovernanceCheck-v2.md` |
| Quality gates | `implementation/v2/quality/QualityAndDelivery-v2.md` |
| GitHub operations | `implementation/v2/workflow/GitHubOperationsManagementGuide-v2.md` |
| CodeX handoff (current task) | `implementation/handoff/current.md` |
| CodeX handoff template | `implementation/handoff/TEMPLATE.md` |

---

## Governance Constraints — Apply to Every Milestone

- **No `InMemory*` in production**: `InMemory*` stubs are test-only. Production code paths must use real clients (PostgreSQL, Redis, OPA). This is a CI and merge gate — grep enforced.
- **Fail-closed default**: Every new code path defaults to deny/block/error on unknown or error state. Never fail-open.
- **Durable-write-first**: Governance-critical events written to PostgreSQL before OTel export. Never reverse.
- **No new roles on mock policy**: DL agent must not be activated until `OPAPolicyRuntimeClient` is live (M12 gate). CSO does not use OPA (Chief Strategy Officer — portfolio advisor); CSO activation is not gated on OPA.
- **Two surfaces only**: Discord (interaction) and Grafana (visualization). No third UI surface in MVP-v2.
- **Alembic migrations**: All DB schema changes via Alembic. `alembic upgrade head` must succeed on a clean database.
- **Rego bundle**: All policy changes must pass `opa check constitution/`. Constitution YAML changes require corresponding Rego bundle updates.

---

## Development Setup

```bash
uv sync --all-groups          # install all dependency groups
uv run alembic upgrade head   # apply migrations to local DB
```

## Test Commands

```bash
# Static checks (always run first)
uv run ruff check .
uv run ruff format --check .
uv run mypy .

# Run a single test file or test by name
uv run pytest tests/unit/test_foo.py
uv run pytest tests/unit/test_foo.py::test_specific_case

# Tier 1 — Fast gate, no compose required (pure-logic unit tests)
uv run pytest -m no_infra tests/unit/

# Tier 2 — Unit + component (no compose required; component tests use in-process stubs)
uv run pytest tests/unit tests/component

# Tier 3 — Full suite (requires compose stack: postgres:5432, redis:6379, opa:8181)
docker compose --profile core up -d
uv run pytest tests/unit tests/component tests/contract tests/integration tests/conformance
```

Test tiers:

- `@pytest.mark.no_infra` — pure-logic tests (grammar parsers, routing tables, state machine guards, schema validators). No I/O. No compose. Auto-applied to all `tests/unit/` tests via `conftest.py`. Run these first for a fast signal.
- `tests/unit tests/component` — runs without compose. Component tests use `patch_build_runtime_services` autouse fixture (in-process stubs injected after `create_control_plane_app()`).
- `tests/contract tests/integration tests/conformance` — require compose stack. Hit real PostgreSQL, Redis, OPA.

Compose stack for integration tests: PostgreSQL `:5432`, Redis `:6379`, OPA `:8181`.

InMemory production path check (run before any PR):
```bash
grep -r --include="*.py" -l "class InMemory" . | grep -v "/testing/" | grep -v "tests/"
# Should return no output. Any match is a merge blocker.
```

---

## Workflow Model

Delivery is WP-based. One WP at a time. WP states: `pending → in_progress → done`.

**GitHub update rule: always update GitHub when WP or milestone state changes.** This includes: new WP added, WP status changed, milestone tracker body changed, new issue created. Never leave GitHub out of sync with the WP document or `ImplementationProgress-v2.md`. Use `gh issue edit` or `gh issue create` immediately after any planning change.

**Starting a WP:**
1. Read the WP document — check entry criteria are met.
2. Mark `in_progress` in `ImplementationProgress-v2.md`.
3. Create a GitHub issue for the WP using the implementation work item template.
4. Update the milestone tracker issue (e.g. #97 for M13) — add the new WP row, update status.
5. Optionally create sub-issues for individual tasks if fine-grained tracking is preferred.

**During implementation:**

- Keep the GitHub issue task checklist updated as tasks complete.
- Add evidence links (test output, command results) to the issue as they are produced.

**Completing a WP:**
1. All task checkboxes in the WP document are checked.
2. All done-criteria are demonstrably met.
3. Mark `done` in `ImplementationProgress-v2.md`.
4. Close the GitHub issue with evidence links.
5. Update the milestone tracker issue — mark WP row `done`, tick exit criterion if applicable.
6. Run deep governance check.

**Per PR:**
- Check off the WP task checkbox that the PR closes.
- Update the GitHub issue checklist and add evidence links for the merged PR.
- Update `ImplementationProgress-v2.md` if WP status changes.
- Run light governance check for structure/docs changes.

Use `/wp`, `/validate`, and `/governance-check` slash commands for these operations.

---

## Bug Fix Backlog

20 architectural review findings (C = critical, H = high, M = medium), each mapped to a milestone and WP. Full list in `ImplementationProgress-v2.md`. Do not introduce new findings of the same class. Resolve each in its assigned WP — do not pull fixes forward or defer them without explicit replanning.

---

## Branch and PR Conventions

Branch format: `<type>/<issue-id>-<short-slug>`
Types: `feat`, `fix`, `infra`, `docs`, `refactor`, `test`, `ci`, `chore`

Merge to `main` via squash merge only. Delete branch after merge.
