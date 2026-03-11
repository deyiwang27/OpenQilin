# OpenQilin v1 Technical Design

Scope:
- Technical designs for implementing the v1 architecture baseline.

Baseline source:
- `spec/architecture/ArchitectureBaseline-v1.md`

Artifact groups:
- `adr/`: architecture decision records
- `components/`: component-level design contracts
- `sequences/`: interaction and runtime sequence designs
- `data/`: schema, storage, migration, and dataflow design
- `foundation/`: toolchain, workstation/config decisions, and framework selection rationale
- `architecture/`: repo layout, module map, app/process topology, and module-level implementation design
- `readiness/`: review records and implementation handoff criteria

Foundation docs:
- `foundation/ImplementationFoundation-v1.md`
- `foundation/ImplementationFrameworkSelection-v1.md`

Implementation execution docs (migrated from `design/v1`):
- `implementation/v1/planning/ImplementationBacklogSeed-v1.md`
- `implementation/v1/planning/ImplementationMilestones-v1.md`
- `implementation/v1/planning/ImplementationExecutionPlan-v1.md`
- `implementation/v1/planning/ImplementationProgress-v1.md`
- `implementation/v1/workflow/DeveloperWorkflowAndContributionGuide-v1.md`
- `implementation/v1/workflow/GitHubOperationsManagementGuide-v1.md`
- `implementation/v1/workflow/AIAssistedDeliveryWorkflow-v1.md`
- `implementation/v1/quality/QualityAndDelivery-v1.md`
- `implementation/v1/quality/ReleaseVersioningAndRollback-v1.md`

Rule:
- Design artifacts must not conflict with `constitution/` or `spec/`.
