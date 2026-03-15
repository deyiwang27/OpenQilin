# OpenQilin v2 - AI Assisted Delivery Workflow

Adapts `implementation/v1/workflow/AIAssistedDeliveryWorkflow-v1.md` for v2. Same control model and loop structure; v2-specific items marked **[v2]**.

---

## 1. Scope

Define a repeatable AI-assisted implementation workflow for OpenQilin v2. Standardize how human operators and Claude Code collaborate from WP selection to merge and WP closeout.

---

## 2. Roles and Control Model

- Human owner/operator controls scope, approvals, and merge decisions.
- Claude Code performs implementation, review support, testing support, and documentation updates within approved scope.
- GitHub Issues/PRs remain the operational source of truth.
- **[v2]** `implementation/v2/planning/ImplementationProgress-v2.md` is the in-repo WP-level status mirror.
- **[v2]** `implementation/v2/planning/05-milestones/` WP documents are the task-level source of truth.

---

## 3. End-to-End Workflow

1. Select the next WP from `MvpV2MilestonePlan-v1.md` and milestone entry gate.
2. Confirm the WP document exists with clear goal, tasks, outputs, and done criteria.
3. Create GitHub issue for the WP (or individual tasks if fine-grained tracking is preferred).
4. Create branch from latest `main` using `<type>/<issue-id>-<short-slug>`.
5. Ask Claude Code for a short implementation plan tied to the WP design doc and relevant `design/v2/` module design.
6. Implement in small increments with frequent local validation.
7. Run required tests/checks by change type (see §6).
8. **[v2]** Run `oq-doctor` after any infrastructure wiring change.
9. Run Claude Code self-review pass before PR creation.
10. Run repository consistency/governance check when applicable.
11. Open PR linked to issue with validation commands and evidence links.
12. Complete merge gate checks, squash merge, delete branch.
13. Check off completed tasks in the WP document; update `ImplementationProgress-v2.md` when WP or milestone status changes.

---

## 4. Ready Gate (Before Coding)

All items must be true before implementation starts:
- WP entry criteria are met (prerequisite milestones/WPs complete)
- tasks in the WP document are clear and scoped
- done criteria are testable
- required design doc is available in `design/v2/`
- **[v2]** for C-series and H-series bug fixes: exact file/line location documented in `ArchitecturalReviewFindings-v2.md`
- rollback expectations are stated for high-risk changes (PostgreSQL migrations, OPA bundle changes)

If any item is missing, update the WP document or design doc first before coding.

---

## 5. Execution Loop (During Coding)

Per WP task, use this loop:
1. `implement` pass: Claude Code applies the smallest coherent code/doc change.
2. `validate` pass: run targeted tests/checks and fix failures.
3. `review` pass: Claude Code performs a focused code review for regressions and policy drift.
4. `sync` pass: update design/spec docs if contracts or migrations changed.

Recommended prompt format to Claude Code per loop:
- `WP ID and task`
- `Done criteria for this task`
- `In scope / out of scope`
- `Required tests`
- `Design doc reference`

---

## 6. Validation Matrix by Change Type

| Change type | Minimum validation |
|---|---|
| Logic/module change | Unit tests required |
| Boundary/adapter change | Component or contract tests required |
| Governed-path change | Integration or conformance coverage required |
| Schema/migration change | Forward-apply validation + regression coverage |
| OPA Rego change | Rego unit tests against authority matrix |
| LangGraph graph change | End-to-end graph test required |
| Infrastructure wiring change | Integration test + `oq-doctor` pass |
| Documentation-only change | Link and consistency checks required |

---

## 7. Merge Gate (Before Merge)

All items must be true before merge:
- PR links at least one issue.
- PR scope is one coherent change set.
- Required checks pass for the change type.
- Verification commands run are documented in PR.
- Done criteria are mapped to concrete evidence (test output or command result).
- Contracts/migrations have matching design/spec updates in the same PR.
- High-risk items include rollback notes.
- **[v2]** No new `InMemory*` class introduced in a production code path.
- **[v2]** WP task checkbox(es) checked in the WP document.

---

## 8. Risk Tiers and Minimum Controls

- `low`: standard review + required tests for touched area.
- `medium`: standard controls + one explicit regression scenario in PR notes.
- `high` (OPA wiring, PostgreSQL migration, LangGraph graph, governance-core path, budget ledger):
  - stricter acceptance evidence
  - integration/conformance validation
  - explicit rollback and containment notes
  - **[v2]** `oq-doctor` evidence after infrastructure change

---

## 9. Post-Merge Closeout

- close the issue with merged PR and evidence links
- check off completed tasks in the WP document
- update `ImplementationProgress-v2.md` when WP or milestone status changes
- create follow-up issues for deferred items instead of expanding merged PR scope
- record any regressions/incidents as new tracked issues

---

## 10. Related Documents

- `implementation/v2/workflow/GitHubOperationsManagementGuide-v2.md`
- `implementation/v2/workflow/DeveloperWorkflowAndContributionGuide-v2.md`
- `implementation/v2/workflow/RepositoryConsistencyAndGovernanceCheck-v2.md`
- `implementation/v2/quality/QualityAndDelivery-v2.md`
- `implementation/v2/planning/05-milestones/MvpV2MilestonePlan-v1.md`
- `implementation/v2/planning/ImplementationProgress-v2.md`
