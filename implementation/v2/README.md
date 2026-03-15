# OpenQilin v2 Implementation Operations

Status: `active — MVP-v2 kickoff approved`
Updated: `2026-03-15`

---

## Scope

Operational guidance, planning, and tracking for MVP-v2 implementation delivery.

---

## Artifact Groups

- `planning/` — direction, product strategy, architecture, community, research, and milestone plans with WP task lists
- `workflow/` — AI-assisted delivery workflow, developer contribution guide, GitHub operations policy, repository consistency check
- `quality/` — quality gates, CI delivery posture, release/rollback operations

---

## Start Here

**For execution (implementation work):**
1. `planning/05-milestones/MvpV2MilestonePlan-v1.md` — master plan with milestone overview and bug fix map
2. `planning/05-milestones/M11-WorkPackages-v1.md` — current active milestone WPs with task checklists
3. `planning/ImplementationProgress-v2.md` — in-repo WP/milestone status mirror

**For workflow (how to work):**
1. `workflow/AIAssistedDeliveryWorkflow-v2.md` — repeatable human+AI delivery loop
2. `workflow/DeveloperWorkflowAndContributionGuide-v2.md` — daily dev loop and command reference

---

## Planning Docs

- `planning/README.md` — full planning artifact index

Key docs:
- `planning/05-milestones/MvpV2MilestonePlan-v1.md` — official milestone plan
- `planning/00-direction/MvpV2SuccessCriteria-v1.md` — success bar
- `planning/00-direction/MvpV2ArchitectureDelta-v1.md` — keep/refactor/replace/defer by component
- `planning/00-direction/ArchitecturalReviewFindings-v2.md` — exhaustive bug/finding backlog with file/line references
- `planning/ImplementationProgress-v2.md` — WP/milestone status tracker

---

## Workflow Docs

- `workflow/AIAssistedDeliveryWorkflow-v2.md`
- `workflow/DeveloperWorkflowAndContributionGuide-v2.md`
- `workflow/GitHubOperationsManagementGuide-v2.md`
- `workflow/RepositoryConsistencyAndGovernanceCheck-v2.md`

---

## Quality Docs

- `quality/QualityAndDelivery-v2.md`
- `quality/ReleaseVersioningAndRollback-v2.md`
- `quality/ReleasePromotionChecklist-v2.md`

---

## Design Artifacts

Implementation-facing design guidance lives in `design/v2/`, not here:
- `design/v2/README.md` — design artifact index and ADR table
- `design/v2/adr/` — ADR-0004 through ADR-0007
- `design/v2/components/` — component delta docs (what changed from v1)
- `design/v2/architecture/` — per-milestone module designs (package layout + interfaces)

---

## Tracking Authority

- GitHub Issues/PRs are the operational source of truth
- `planning/ImplementationProgress-v2.md` is the in-repo WP/milestone status mirror
- WP documents in `planning/05-milestones/` are the task-level source of truth
