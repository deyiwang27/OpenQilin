# OpenQilin v2 - GitHub Operations Management Guide

Adapts `implementation/v1/workflow/GitHubOperationsManagementGuide-v1.md` for v2. Same operational structure; v2-specific items marked **[v2]**.

---

## 1. Scope

Define the operational workflow for managing GitHub Issues, Pull Requests, labels, milestones, and releases during v2 implementation. Standardize how WP-level progress is captured and synchronized back to repository planning docs.

---

## 2. Operational Source of Truth

- GitHub Issues/PRs/Project are the primary execution tracking system.
- **[v2]** `implementation/v2/planning/ImplementationProgress-v2.md` is the in-repo mirror for WP/milestone-level status and evidence.
- `main` is the integration branch for implementation PRs.

---

## 3. Access and Tooling Prerequisites

- GitHub CLI must be available and authenticated:
  - `gh auth status`
  - `gh repo set-default deyiwang27/OpenQilin`
- Required token scopes: `repo`, `read:org` (when needed), `project` (when using GitHub Projects)

---

## 4. Issue Management Standard

Issue template: `.github/ISSUE_TEMPLATE/implementation_work_item.yml`

### 4.1 Issue Required Fields

Each implementation issue should include:
- `Milestone` (e.g. M11, M12)
- **[v2]** `WP` (e.g. M12-WP3)
- `Goal`
- `Scope`
- `Acceptance Criteria` (maps directly to WP done-criteria)
- `Dependencies` (WP entry criteria)
- `Evidence Links`
- `Definition of Done`

### 4.2 Label Taxonomy

Use consistent labels:
- `milestone:*` (e.g. `milestone:M11`, `milestone:M12`)
- **[v2]** `wp:*` (e.g. `wp:M12-WP3`) for WP-level tracking
- `type:*` (e.g. `type:feature`, `type:fix`, `type:infra`, `type:docs`)
- `area:*` (e.g. `area:control_plane`, `area:task_orchestrator`, `area:budget_runtime`, `area:observability`)
- `risk:*` (e.g. `risk:governance-core`, `risk:schema-migration`, `risk:opa-bundle`)
- **[v2]** `bug:*` (e.g. `bug:C-1`, `bug:H-3`) for architectural review bug fix tracking

### 4.3 Issue Lifecycle

1. Create issue with complete required fields.
2. Assign milestone, WP, and labels before implementation starts.
3. Link issue in branch name and PR.
4. Keep WP task checklist updated as implementation progresses.
5. Close issue only after merge and evidence links are complete.
6. Check off the corresponding task in the WP document after merge.

---

## 5. Branch and PR Operations

PR template: `.github/pull_request_template.md`

### 5.1 Branch Naming

Branch format: `<type>/<issue-id>-<short-slug>`

Examples:
- `feat/101-m12-opa-client-wiring`
- `fix/108-h1-fail-open-dispatch`
- `infra/115-m12-postgres-migration`
- `docs/120-design-v2-adr-0006`

### 5.2 PR Standard

- Every PR links at least one issue (`Closes #101`).
- PR scope remains one coherent change set (one WP task or tightly related group).
- PR description includes exact local verification commands executed.
- Contract or migration changes must include corresponding design/spec updates.
- **[v2]** OPA Rego changes must include Rego unit test evidence.
- **[v2]** Alembic migration PRs must include forward-apply evidence on a clean DB.
- Repository consistency/governance check evidence required for structure/policy/docs changes.

### 5.3 Merge Standard

- Use squash merge.
- Delete branch after merge.
- Required checks and approvals must pass before merge.
- **[v2]** After merge: check off WP task; update `ImplementationProgress-v2.md` if WP status changes.

---

## 6. Release and Hotfix Operations

Release posture:
- Cut `v0.2.z` tags from `main` during MVP-v2.
- Avoid long-lived `release/*` branches.
- Each release must pass the promotion checklist: `implementation/v2/quality/ReleasePromotionChecklist-v2.md`.

Hotfix posture:
- Branch from latest `main` using `fix/<issue-id>-<slug>`.
- Open fast-track PR with same checks/approvals.
- Squash merge to `main`, then tag if required.

---

## 7. Progress and Evidence Synchronization

- **[v2]** WP cadence: update WP task checkboxes and `ImplementationProgress-v2.md` after each merged PR that completes a WP task.
- PR cadence: each merged PR updates issue acceptance checklists and evidence links.
- Milestone closeout: all linked WPs must have exit criteria confirmed before milestone is marked complete.
- Milestone closeout requires deep-level governance check evidence.

---

## 8. GitHub CLI Command Reference

Issue operations:
```bash
gh issue create --title "M12-WP3: PostgreSQL repository migration" --body-file /tmp/issue.md
gh issue edit 101 --add-label "milestone:M12,wp:M12-WP3,type:infra,area:data_access,risk:schema-migration"
gh issue list --state open --label milestone:M12
gh issue close 101 --comment "Completed in #115. WP M12-WP3 task 3 checked."
```

PR operations:
```bash
gh pr create --base main --head infra/115-m12-postgres-migration --title "M12-WP3: PostgreSQL repository migration" --body-file /tmp/pr.md
gh pr view 115 --web
gh pr checks 115 --watch
gh pr merge 115 --squash --delete-branch
```

Milestone and release operations:
```bash
gh api repos/deyiwang27/OpenQilin/milestones
gh release create v0.2.0 --generate-notes
```

**[v2]** WP tracking operations:
```bash
# List all open WP issues for a milestone
gh issue list --state open --label milestone:M12

# List all bug-fix issues
gh issue list --label "bug:C-1,bug:H-1,bug:H-2" --state open
```

---

## 9. Governance Checklist for GitHub Settings

Same as v1 — enforce:
- branch protection on `main`
- block direct pushes
- required status checks
- required PR review approvals
- up-to-date branch requirement before merge
- squash merge enabled
- branch auto-delete after merge

Fallback for repositories where branch protection is unavailable:
- enforce issue-linked PR-only merges operationally
- enforce squash merge and branch delete manually at merge time
- treat CI green + reviewer approval as hard gate before merge

---

## 10. Related Documents

- `implementation/v2/workflow/AIAssistedDeliveryWorkflow-v2.md`
- `implementation/v2/workflow/DeveloperWorkflowAndContributionGuide-v2.md`
- `implementation/v2/workflow/RepositoryConsistencyAndGovernanceCheck-v2.md`
- `implementation/v2/quality/QualityAndDelivery-v2.md`
- `implementation/v2/planning/05-milestones/MvpV2MilestonePlan-v1.md`
- `implementation/v2/planning/ImplementationProgress-v2.md`
