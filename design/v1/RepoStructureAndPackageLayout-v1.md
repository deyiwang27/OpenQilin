# OpenQilin v1 - Repo Structure and Package Layout

## 1. Scope
- Define the top-level repository structure for v1 implementation.
- Define the initial Python package layout and app entrypoint placement.
- Keep the structure simple enough for local-first development.

## 2. v1 Decision
Repository posture:
- single repository
- single root Python project managed by `uv`
- one shared package tree for runtime code
- multiple runnable app entrypoints

Do not use for v1:
- multi-repo split
- Python monorepo workspace with multiple independent package locks

## 3. Proposed Top-Level Structure
```text
OpenQilin/
  constitution/
  spec/
  design/
  docs/
  src/
    openqilin/
      apps/
      shared_kernel/
      control_plane/
      task_orchestrator/
      policy_runtime_integration/
      budget_runtime/
      llm_gateway/
      communication_gateway/
      execution_sandbox/
      data_access/
      observability/
  tests/
    unit/
    component/
    contract/
    integration/
    conformance/
  migrations/
  ops/
    docker/
    bootstrap/
    scripts/
  pyproject.toml
  uv.lock
  README.md
```

## 4. Package Layout Rules
### 4.1 `src/openqilin/apps/`
Purpose:
- runnable process entrypoints only

Expected apps:
- `api.py`
- `orchestrator_worker.py`
- `communication_worker.py`
- `admin_cli.py`

### 4.2 `src/openqilin/shared_kernel/`
Purpose:
- shared types, config loading, error envelopes, identifiers, and cross-module utilities

Rules:
- may be depended on by all runtime modules
- must not accumulate feature-specific orchestration logic

### 4.3 Runtime Modules
Each runtime module gets its own package:
- `control_plane/`
- `task_orchestrator/`
- `policy_runtime_integration/`
- `budget_runtime/`
- `llm_gateway/`
- `communication_gateway/`
- `execution_sandbox/`
- `data_access/`
- `observability/`

Rules:
- feature logic stays inside its owning module
- cross-module access should happen through explicit interfaces, not deep imports

## 5. Tests Layout
`tests/unit/`
- isolated module-level tests

`tests/component/`
- tests against one runtime component with fakes/stubs

`tests/contract/`
- validation of spec-aligned request/response/error contracts

`tests/integration/`
- multi-component tests with real infrastructure dependencies where needed

`tests/conformance/`
- governance-core and recovery/smoke validation

## 6. Infrastructure and Ops Layout
`migrations/`
- schema migrations only

`ops/docker/`
- Docker Compose and container-related assets

`ops/bootstrap/`
- local seed/bootstrap material

`ops/scripts/`
- operational helper scripts that are not application code

## 7. Why This Layout
- keeps implementation code separate from specification/design documents
- supports multiple app entrypoints without splitting the project too early
- keeps tests explicit by layer
- keeps infra/bootstrap artifacts visible at the repo root

## 8. Future Evolution
Possible later changes if v1 grows:
- split some runtime modules into separate deployable packages
- introduce a workspace layout if dependency isolation becomes necessary
- add deployment manifests for later cloud/Kubernetes phases outside the v1 local baseline

## 9. Related Design Follow-Ups
- module dependency rules belong in `ModuleDependencyMap-v1.md`
- app/process ownership belongs in `AppEntrypointsAndProcessTopology-v1.md`
- test layout details belong in `TestStrategyAndLayout-v1.md`
