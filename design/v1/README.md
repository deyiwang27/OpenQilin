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
- `foundation/`: toolchain, workstation, configuration, framework selection, and developer workflow guidance
- `architecture/`: repo layout, module map, app and process topology, container topology, and module-level implementation design
- `quality/`: testing strategy, CI/CD design, and release/rollback workflow
- `planning/`: implementation backlog, milestone planning, execution plan, and progress ledger
- `readiness/`: review records and implementation handoff criteria

Foundation docs:
- `foundation/ImplementationFoundation-v1.md`
- `foundation/ImplementationFrameworkSelection-v1.md`
- `foundation/DeveloperWorkflowAndContributionGuide-v1.md`
- `foundation/GitHubOperationsManagementGuide-v1.md`

Planning docs:
- `planning/ImplementationBacklogSeed-v1.md`
- `planning/ImplementationMilestones-v1.md`
- `planning/ImplementationExecutionPlan-v1.md`
- `planning/ImplementationProgress-v1.md`

Rule:
- Design artifacts must not conflict with `constitution/` or `spec/`.
