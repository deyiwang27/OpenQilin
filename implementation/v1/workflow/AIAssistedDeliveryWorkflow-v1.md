# OpenQilin v1 - AI Assisted Delivery Workflow

## 1. Scope
- Define a repeatable AI-assisted implementation workflow for OpenQilin v1.
- Standardize how human operators and Codex collaborate from issue selection to merge and closeout.

## 2. Roles and Control Model
- Human owner/operator controls scope, approvals, and merge decisions.
- Codex performs implementation, review support, testing support, and documentation updates within approved scope.
- GitHub Issues/PRs remain the operational source of truth; planning docs remain milestone/status mirrors.

## 3. End-to-End Workflow
1. Select the next work item from `ImplementationProgress-v1.md` and milestone dependencies.
2. Confirm issue exists and is complete (goal, scope, acceptance criteria, dependencies, evidence, definition of done).
3. Create branch from latest `main` using `<type>/<issue-id>-<short-slug>`.
4. Ask Codex for a short implementation plan tied to existing design/spec docs.
5. Implement in small increments with frequent local validation.
6. Run required tests/checks by change type.
7. Run Codex self-review pass before PR creation.
8. Open PR linked to issue (`Closes #...`) with validation commands and evidence links.
9. Complete merge gate checks, squash merge, and delete branch.
10. Close issue and update `ImplementationProgress-v1.md` when milestone status/evidence changed.

## 4. Ready Gate (Before Coding)
All items must be true before implementation starts:
- issue has clear in-scope and out-of-scope boundaries
- acceptance criteria are testable
- dependencies are resolved or explicitly tracked
- milestone label and risk label are assigned
- required evidence format is defined (test output, trace/audit links, screenshots/logs where needed)
- rollback expectations are stated for high-risk changes

If any item is missing, update the issue first before coding.

## 5. Execution Loop (During Coding)
Per issue, use this loop:
1. `implement` pass: Codex applies smallest coherent code/doc change.
2. `validate` pass: run targeted tests/checks and fix failures.
3. `review` pass: Codex performs a focused code review for regressions and policy drift.
4. `sync` pass: update docs/spec if contracts or migrations changed.

Recommended prompt format to Codex per loop:
- `Issue ID`
- `Acceptance Criteria`
- `In Scope / Out of Scope`
- `Required tests`
- `Evidence expected in PR`

## 6. Validation Matrix by Change Type
- Logic/module changes: unit tests required.
- Adapter or boundary changes: component or contract tests required.
- Governed-path behavior changes: integration or conformance coverage required.
- Schema/migration changes: forward-apply migration validation and regression coverage required.
- Documentation-only changes: link and consistency checks required.

## 7. Merge Gate (Before Merge)
All items must be true before merge:
- PR links at least one issue.
- PR scope is one coherent change set.
- required checks pass for the change type.
- verification commands run are documented in PR.
- acceptance criteria are mapped to concrete evidence links.
- contracts/migrations have matching design/spec updates in the same PR.
- high-risk items include rollback notes.

## 8. Risk Tiers and Minimum Controls
- `low`: standard review + required tests for touched area.
- `medium`: standard controls + one explicit regression scenario in PR notes.
- `high` (`risk:governance-core`, data migration, critical runtime path):
  - stricter acceptance evidence
  - integration/conformance validation when applicable
  - explicit rollback and containment notes

## 9. Post-Merge Closeout
- close the issue with merged PR and evidence links.
- update milestone progress/evidence in `ImplementationProgress-v1.md` when changed.
- create follow-up issues for deferred items instead of expanding merged PR scope.
- record any regressions/incidents as new tracked issues.

## 10. Related Documents
- `implementation/v1/workflow/GitHubOperationsManagementGuide-v1.md`
- `implementation/v1/workflow/DeveloperWorkflowAndContributionGuide-v1.md`
- `implementation/v1/quality/QualityAndDelivery-v1.md`
- `implementation/v1/planning/ImplementationExecutionPlan-v1.md`
- `implementation/v1/planning/ImplementationProgress-v1.md`
