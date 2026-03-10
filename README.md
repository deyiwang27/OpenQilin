# OpenQilin

OpenQilin is a governance-first AI workforce orchestration architecture.

The goal is to help a solopreneur operate a coordinated, long-running AI organization with clear authority, safety controls, and budget discipline.

## Current Status

This repository is currently **documentation-first**.

- Define phase is complete at baseline level.
- v1 architecture baseline is published.
- Next phase is technical design, then implementation.

## Core Idea

OpenQilin models AI operation as a constitutional governance system:

- Strategic and operational roles are separated.
- Governance is independent from execution.
- Policies are explicit, versioned, and auditable.
- Runtime actions are constrained by authority, budget, and safety rules.

## Development Flow

OpenQilin follows:
1. `Define` (constitution + implementation contracts in `spec/`)
2. `Design` (technical design artifacts in `design/`)
3. `Implementation` (code/services/tests)

## v1 Architecture Baseline

The implementation kickoff baseline is:
- [`spec/architecture/ArchitectureBaseline-v1.md`](spec/architecture/ArchitectureBaseline-v1.md)

It locks:
- selected stack decisions
- component boundary mapping
- authoritative v1 interfaces (`policy`, `task`, `a2a+acp`, `llm_gateway`, `memory`, `audit`)
- deployment phase posture (`local-first`, then cloud promotion)

## Repository Structure

- `spec/`: implementation-level specifications for AI engineering agents
- `docs/`: concise human-facing documentation for GitHub users
- `constitution/`: constitutional runtime rules that agents must follow
- `design/`: technical design artifacts for the current design cycle (initialized in design branch)

Precedence:

1. `constitution/` (runtime constitutional source of truth)
2. `spec/` (implementation contract)
3. `design/` (technical design, must not violate constitution/spec)
4. `docs/` (human-readable guidance)

## Start Here

If you are new to the project:

1. Read [`docs/SystemOverview.md`](docs/SystemOverview.md)
2. Read [`docs/QuickStart.md`](docs/QuickStart.md)
3. Read [`spec/architecture/ArchitectureBaseline-v1.md`](spec/architecture/ArchitectureBaseline-v1.md)
4. Read [`spec/governance/architecture/GovernanceArchitecture.md`](spec/governance/architecture/GovernanceArchitecture.md)
5. Read [`spec/infrastructure/architecture/RuntimeArchitecture.md`](spec/infrastructure/architecture/RuntimeArchitecture.md)
6. Read constitutional files in `constitution/`

## Key Specifications

- Architecture baseline: [`spec/architecture/ArchitectureBaseline-v1.md`](spec/architecture/ArchitectureBaseline-v1.md)
- Governance architecture: [`spec/governance/architecture/GovernanceArchitecture.md`](spec/governance/architecture/GovernanceArchitecture.md)
- Runtime architecture: [`spec/infrastructure/architecture/RuntimeArchitecture.md`](spec/infrastructure/architecture/RuntimeArchitecture.md)
- Policy engine: [`spec/constitution/PolicyEngineContract.md`](spec/constitution/PolicyEngineContract.md)
- Task orchestration: [`spec/orchestration/control/TaskOrchestrator.md`](spec/orchestration/control/TaskOrchestrator.md)
- Execution sandbox: [`spec/infrastructure/security/ExecutionSandbox.md`](spec/infrastructure/security/ExecutionSandbox.md)
- Observability: [`spec/observability/ObservabilityArchitecture.md`](spec/observability/ObservabilityArchitecture.md)

## Constitution Layer

The `constitution/` folder defines enforceable constitutional policy artifacts, including:

- authority matrix
- policy rules
- escalation policy
- budget policy
- safety policy
- policy change control

These artifacts are expected to be versioned and referenced at runtime via policy version/hash metadata.

Version snapshot example:
- `constitution/versions/v0.1.0/`

## Contributing

At this stage, contributions should prioritize:

- clarity and consistency of rules
- deterministic contracts (inputs/outputs/errors)
- explicit state transitions and escalation paths
- conformance-test readiness
- consistency between `constitution/`, `spec/`, and conformance artifacts

For major changes, keep PRs scoped to one layer (`constitution`, `spec`, or `docs`) where possible.

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file.
