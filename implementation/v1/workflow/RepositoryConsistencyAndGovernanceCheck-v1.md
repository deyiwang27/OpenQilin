# OpenQilin v1 - Repository Consistency and Governance Check

## 1. Scope
- Define the repeatable check process for repository consistency, policy alignment, and information architecture hygiene.
- Prevent drift after large refactors, milestone closes, and process/document updates.

## 2. Authority and Outcomes
- GitHub Issues/PRs/Project remain execution source of truth.
- Check outcomes are recorded in PR evidence and reflected in `implementation/v1/planning/ImplementationProgress-v1.md` when milestone status or blockers change.
- This check does not replace code/test quality gates; it complements them.

Possible outcomes:
- `pass`
- `pass_with_followups`
- `blocked`

## 3. Trigger Policy
Run this check in two levels:

### 3.1 PR-Level (Light)
Run for every PR to `main`.

Minimum scope:
- path/link consistency for touched docs
- authority wording consistency for touched governance/planning docs
- branch/issue/PR policy compliance

### 3.2 Deep-Level (Governance)
Run when any of the following is true:
- milestone close or weekly implementation review
- major folder/file migration or rename
- new top-level or major subfolder added
- 3+ docs added in one area
- process/policy document added or renamed
- pre-release tagging

## 4. Check Matrix
1. Structure integrity:
- no accidental empty/orphan folders
- files located in folder matching scope/ownership

2. Reference integrity:
- no stale paths after move/rename
- canonical docs are referenced consistently

3. Authority consistency:
- no contradiction in source-of-truth statements
- design/spec/implementation boundary statements stay coherent

4. Tracking consistency:
- issue/PR evidence aligns with progress and TODO mirrors
- milestone blockers/status entries match current implementation reality

5. Information architecture drift (mandatory):
- folder-fit check: file belongs to current folder charter
- duplication check: overlapping docs are merged or one marked canonical
- split/merge/migrate check: older files are migrated when new structure supersedes them
- ownership check: each policy/process has one canonical owner document

6. Placeholder and debt visibility:
- unresolved `TODO`/placeholder items are tracked as planned work or blockers

7. Quality baseline:
- `ruff`, `mypy`, and required pytest slices pass for current scope

8. Contract and governance drift:
- contract-impacting changes include aligned spec/design updates
- PR/issue templates and workflow docs still enforce current policy

## 5. Evidence Contract
Every deep-level check should capture:
- check scope (`PR` or `weekly/milestone`)
- result (`pass`, `pass_with_followups`, `blocked`)
- key findings and decisions (move/merge/keep with rationale)
- evidence links (PR, issue, test command outputs, updated docs)

## 6. Enforcement Actions
- PR template requires confirmation that consistency/governance checks are completed when applicable.
- GitHub operations policy requires milestone-level governance check evidence before milestone close.
- Quality policy treats unresolved high-risk governance drift as merge/release blocker.
- Follow-up actions must be tracked as issues when not resolved in the current PR.

## 7. Decision Rules for Reorganization
When files/folders drift:
1. Move:
- file scope matches another folder better than current one

2. Merge:
- two docs duplicate policy/process guidance and can share a canonical owner

3. Keep split:
- documents have distinct audience/scope and cross-reference the canonical source

4. Delete:
- obsolete duplicate no longer adds unique value and has a replacement

## 8. Related Documents
- `implementation/v1/workflow/DeveloperWorkflowAndContributionGuide-v1.md`
- `implementation/v1/workflow/GitHubOperationsManagementGuide-v1.md`
- `implementation/v1/quality/QualityAndDelivery-v1.md`
- `implementation/v1/planning/ImplementationExecutionPlan-v1.md`
- `implementation/v1/planning/ImplementationProgress-v1.md`
- `.github/pull_request_template.md`
