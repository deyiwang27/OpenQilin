## Summary
- What changed and why.

## Linked Issue
- Closes #

## Milestone / WP
- Milestone: M11 / M12 / M13 / M14 / M15 / M16
- WP: e.g. M12-WP3

## Scope
- In scope:
- Out of scope:

## Validation Commands Run
```bash
# Example:
# uv run pytest tests/unit tests/component
# uv run ruff check .
# uv run mypy .
```

## Evidence Links
- Issue:
- Test run:
- Trace/Audit (if governed path impacted):
- Alembic forward-apply (if DB migration included):
- OPA Rego unit tests (if Rego bundle changed):
- Governance check (if structure/policy/docs changed):

## Policy and Quality Checklist
- [ ] Branch name follows `<type>/<issue-id>-<short-slug>`.
- [ ] PR scope is one coherent change set.
- [ ] PR links at least one issue.
- [ ] Local verification commands are listed above.
- [ ] Required checks for this change type are green.
- [ ] Contract or migration changes include corresponding design/spec updates.
- [ ] No `InMemory*` class introduced in any production code path (only allowed under `testing/` subpackages).
- [ ] WP task checkbox checked in the WP document if this PR completes a WP task.
- [ ] `implementation/v2/planning/ImplementationProgress-v2.md` updated when WP/milestone status changed.
- [ ] Repository consistency/governance checks completed when applicable (`implementation/v2/workflow/RepositoryConsistencyAndGovernanceCheck-v2.md`).

## Reviewer Notes
- Risks:
- Follow-ups:
