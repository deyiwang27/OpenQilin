# OpenQilin v1 - GitHub Operations Management Guide

## 1. Scope
- Define the operational workflow for managing GitHub Issues, Pull Requests, labels, milestones, and releases during v1 implementation.
- Standardize how implementation evidence is captured and synchronized back to repository planning docs.

## 2. Operational Source of Truth
- GitHub Issues/PRs/Project are the primary execution tracking system.
- `design/v1/planning/ImplementationProgress-v1.md` is the in-repo mirror for milestone-level status and evidence.
- `main` is the integration branch for implementation PRs.

## 3. Access and Tooling Prerequisites
- GitHub CLI must be available and authenticated:
  - `gh auth status`
  - `gh repo set-default deyiwang27/OpenQilin`
- Required token scopes for maintainers/operators:
  - `repo`
  - `read:org` (when needed)
  - `project` (when using GitHub Projects)

## 4. Issue Management Standard
Issue template:
- `.github/ISSUE_TEMPLATE/implementation_work_item.yml`

### 4.1 Issue Required Fields
Each implementation issue should include:
- `Milestone`
- `Goal`
- `Scope`
- `Acceptance Criteria`
- `Dependencies`
- `Evidence Links`
- `Definition of Done`

### 4.2 Label Taxonomy
Use consistent labels:
- `milestone:*` (example: `milestone:M1`)
- `type:*` (example: `type:feature`, `type:test`, `type:infra`, `type:docs`)
- `area:*` (example: `area:control_plane`, `area:task_orchestrator`)
- `risk:*` (example: `risk:governance-core`)

### 4.3 Issue Lifecycle
1. Create issue with complete required fields.
2. Assign milestone and labels before implementation starts.
3. Link issue in branch name and PR.
4. Keep acceptance checklist updated as implementation progresses.
5. Close issue only after merge and evidence links are complete.

## 5. Branch and PR Operations
PR template:
- `.github/pull_request_template.md`

### 5.1 Branch Naming
Branch format:
- `<type>/<issue-id>-<short-slug>`

Examples:
- `feat/4-m1-governed-path-kickoff`
- `fix/27-policy-timeout-retry`
- `docs/31-github-ops-guide`

### 5.2 PR Standard
- Every PR links at least one issue (for example, `Closes #4`).
- PR scope remains one coherent change set.
- PR description includes exact local verification commands executed.
- Contract or migration changes must include corresponding design/spec updates.

### 5.3 Merge Standard
- Use squash merge.
- Delete branch after merge.
- Ensure required checks and approvals are satisfied before merge.

## 6. Release and Hotfix Operations
Release posture:
- Cut `v0.y.z` tags from `main` during v1.
- Avoid long-lived `release/*` branches.
- If temporary release branch is required, delete it after stabilization.

Hotfix posture:
- Branch from latest `main` using `fix/<issue-id>-<slug>`.
- Open fast-track PR with same checks/approvals.
- Squash merge to `main`, then tag if required.

## 7. Progress and Evidence Synchronization
- Weekly cadence: update `ImplementationProgress-v1.md` with status, blockers, and evidence links.
- PR cadence: each merged PR should update issue acceptance checklists and evidence links.
- Milestone closeout: validate all linked feature issues are closed with evidence before closing milestone status.

## 8. GitHub CLI Command Reference
Issue operations:
```bash
gh issue create --title "M1: Example Feature" --body-file /tmp/issue.md
gh issue edit 4 --add-label milestone:M1,type:feature,area:control_plane,risk:governance-core
gh issue list --state open --label milestone:M1
gh issue close 4 --comment "Completed in #12"
```

PR operations:
```bash
gh pr create --base main --head feat/4-m1-governed-path-kickoff --title "M1: governed path kickoff" --body-file /tmp/pr.md
gh pr view 12 --web
gh pr checks 12 --watch
gh pr merge 12 --squash --delete-branch
```

Milestone and release operations:
```bash
gh api repos/deyiwang27/OpenQilin/milestones
gh release create v0.1.0 --generate-notes
```

## 9. Governance Checklist for GitHub Settings
Repository administrators should enforce:
- branch protection on `main`
- block direct pushes to `main`
- required status checks
- required PR review approvals
- up-to-date branch requirement before merge
- squash merge enabled
- branch auto-delete after merge

## 10. Related Documents
- `design/v1/foundation/AIAssistedDeliveryWorkflow-v1.md`
- `design/v1/foundation/DeveloperWorkflowAndContributionGuide-v1.md`
- `design/v1/quality/QualityAndDelivery-v1.md`
- `design/v1/planning/ImplementationExecutionPlan-v1.md`
- `design/v1/planning/ImplementationProgress-v1.md`
