# OpenQilin v2 - Repository Consistency and Governance Check

Adapts `implementation/v1/workflow/RepositoryConsistencyAndGovernanceCheck-v1.md` for v2. Same check matrix; v2-specific additions marked **[v2]**.

---

## 1. Scope

Define the repeatable check process for repository consistency, policy alignment, and information architecture hygiene for v2. Prevent drift after large refactors, WP closes, and process/document updates.

---

## 2. Authority and Outcomes

- GitHub Issues/PRs/Project remain execution source of truth.
- Check outcomes recorded in PR evidence and reflected in `ImplementationProgress-v2.md` when WP/milestone status or blockers change.
- This check does not replace code/test quality gates; it complements them.

Possible outcomes:
- `pass`
- `pass_with_followups`
- `blocked`

---

## 3. Trigger Policy

### 3.1 PR-Level (Light)

Run for every PR to `main`.

Minimum scope:
- path/link consistency for touched docs
- authority wording consistency for touched governance/planning docs
- branch/issue/PR policy compliance
- **[v2]** WP task checkbox updated if PR completes a WP task

### 3.2 Deep-Level (Governance)

Run when any of the following is true:
- WP close or milestone close
- major folder/file migration or rename
- new top-level or major subfolder added
- 3+ docs added in one area
- process/policy document added or renamed
- pre-release tagging
- **[v2]** any InMemory stub moved to or removed from `testing/`
- **[v2]** OPA Rego bundle structure changed
- **[v2]** new Alembic migration added

---

## 4. Check Matrix

**1. Structure integrity:**
- no accidental empty/orphan folders
- files located in folder matching scope/ownership
- **[v2]** `InMemory*` classes only under `testing/` subpackages; none in production paths

**2. Reference integrity:**
- no stale paths after move/rename
- canonical docs referenced consistently
- **[v2]** WP documents reference correct `design/v2/` module design docs
- **[v2]** `ImplementationProgress-v2.md` WP status entries match current WP task checkboxes

**3. Authority consistency:**
- no contradiction in source-of-truth statements
- design/spec/implementation boundary statements coherent
- **[v2]** `spec/` remains normatively above `design/v2/` which remains above `implementation/v2/`

**4. Tracking consistency:**
- issue/PR evidence aligns with WP task checkboxes and progress mirror
- WP blockers/status entries match current implementation reality
- **[v2]** closed WPs have all done-criteria demonstrably met (not just tasks checked)

**5. Information architecture drift (mandatory):**
- folder-fit check: file belongs to current folder charter
- duplication check: overlapping docs merged or one marked canonical
- split/merge/migrate check: older files migrated when new structure supersedes them
- ownership check: each policy/process has one canonical owner document
- **[v2]** `00-direction/archive/` contains only superseded docs; no active reference docs

**6. Placeholder and debt visibility:**
- unresolved `TODO`/placeholder items tracked as planned work or blockers
- **[v2]** all empty placeholder modules (`pass` bodies) in source are tracked as open WP tasks

**7. Quality baseline:**
- `ruff`, `mypy`, and required pytest slices pass for current scope
- **[v2]** Alembic `upgrade head` succeeds on a clean database
- **[v2]** OPA Rego bundle loads without error

**8. Contract and governance drift:**
- contract-impacting changes include aligned spec/design updates
- PR/issue templates and workflow docs enforce current policy
- **[v2]** changes to `constitution/core/` YAML files have corresponding Rego bundle updates

---

## 5. Evidence Contract

Every deep-level check should capture:
- check scope (`PR`, `WP-close`, `milestone-close`, or `pre-release`)
- result (`pass`, `pass_with_followups`, `blocked`)
- key findings and decisions (move/merge/keep with rationale)
- evidence links (PR, issue, test command outputs, updated docs)

---

## 6. Enforcement Actions

- PR template requires confirmation that consistency/governance checks are completed when applicable.
- GitHub operations policy requires WP-level governance check evidence before WP marked complete.
- Quality policy treats unresolved high-risk governance drift as merge/release blocker.
- Follow-up actions tracked as issues when not resolved in the current PR.

---

## 7. Decision Rules for Reorganization

When files/folders drift:
1. **Move** — file scope matches another folder better than current
2. **Merge** — two docs duplicate policy/process guidance and can share a canonical owner
3. **Keep split** — documents have distinct audience/scope and cross-reference the canonical source
4. **Archive** — superseded doc: move to `archive/` subfolder; do not delete (preserves design history)
5. **Delete** — truly obsolete duplicate with no design history value and a clear replacement

---

## 8. Related Documents

- `implementation/v2/workflow/DeveloperWorkflowAndContributionGuide-v2.md`
- `implementation/v2/workflow/GitHubOperationsManagementGuide-v2.md`
- `implementation/v2/quality/QualityAndDelivery-v2.md`
- `implementation/v2/planning/05-milestones/MvpV2MilestonePlan-v1.md`
- `implementation/v2/planning/ImplementationProgress-v2.md`
- `.github/pull_request_template.md`
