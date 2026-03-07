# OpenQilin

OpenQilin is a governance-first AI workforce orchestration architecture.

The goal is to help a solopreneur operates a coordinated, long-running AI organization with clear authority, safety controls, and budget discipline.

## Current Status

This repository is currently **documentation-first**.

- System governance, authority, runtime, and policy contracts are being defined.
- The implementation phase should follow these documents.

## Core Idea

OpenQilin models AI operation as an institutional system:

- Strategic and operational roles are separated.
- Governance is independent from execution.
- Policies are explicit, versioned, and auditable.
- Runtime actions are constrained by authority, budget, and safety rules.

## Repository Structure

- `spec/`: implementation-level specifications for AI engineering agents
- `docs/`: concise human-facing documentation for GitHub users
- `constitution/`: institutional runtime rules that agents must follow

Precedence:

1. `constitution/` (runtime institutional source of truth)
2. `spec/` (implementation contract)
3. `docs/` (human-readable guidance)

## Start Here

If you are new to the project:

1. Read [`docs/SystemOverview.md`](docs/SystemOverview.md)
2. Read [`docs/QuickStart.md`](docs/QuickStart.md)
3. Read [`spec/Governance.md`](spec/Governance.md)
4. Read [`spec/RuntimeInfrastructure.md`](spec/RuntimeInfrastructure.md)
5. Read constitutional files in `constitution/`

## Key Specifications

- Governance architecture: [`spec/Governance.md`](spec/Governance.md)
- Runtime architecture: [`spec/RuntimeInfrastructure.md`](spec/RuntimeInfrastructure.md)
- Policy engine: [`spec/PolicyEngine.md`](spec/PolicyEngine.md)
- Task orchestration: [`spec/TaskOrchestrator.md`](spec/TaskOrchestrator.md)
- Execution sandbox: [`spec/ExecutionSandbox.md`](spec/ExecutionSandbox.md)
- Observability: [`spec/Observability.md`](spec/Observability.md)

## Constitution Layer

The `constitution/` folder defines enforceable institutional policy artifacts, including:

- authority matrix
- policy rules
- escalation policy
- budget policy
- safety policy
- policy change control

These artifacts are expected to be versioned and referenced at runtime via policy version/hash metadata.

## Contributing

At this stage, contributions should prioritize:

- clarity and consistency of rules
- deterministic contracts (inputs/outputs/errors)
- explicit state transitions and escalation paths
- conformance-test readiness

For major changes, keep PRs scoped to one layer (`constitution`, `spec`, or `docs`) where possible.

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file.
