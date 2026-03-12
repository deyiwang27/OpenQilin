# OpenQilin v1 - Implementation Architecture

## 1. Scope
- Define the top-level implementation structure for the repo.
- Consolidate package layout, module dependency rules, runnable app topology, and module hosting decisions.

## 2. Repository and Package Layout
v1 posture:
- single repository
- single root Python project managed by `uv`
- shared `src/openqilin/` package tree
- multiple runnable app entrypoints

Proposed top-level structure:
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
```

## 3. Major Modules
- `shared_kernel`
- `control_plane`
- `task_orchestrator`
- `policy_runtime_integration`
- `budget_runtime`
- `llm_gateway`
- `communication_gateway`
- `execution_sandbox`
- `data_access`
- `observability`

## 4. Dependency Rules
Allowed:
- `apps -> runtime modules`
- `runtime modules -> shared_kernel`
- `runtime modules -> data_access` where persistence ownership requires it
- `runtime modules -> observability` for telemetry and audit emission only

Forbidden:
- `shared_kernel -> feature modules`
- direct control-plane calls to sandbox, tool, or provider execution
- communication gateway mutating task business state
- execution sandbox making policy decisions
- llm gateway owning orchestration logic

## 5. Runtime Module Responsibilities
### 5.1 `shared_kernel`
- identifiers, DTOs, error envelopes, config primitives, cross-cutting helpers

### 5.2 `control_plane`
- FastAPI routes, ingress validation, identity binding, command/query handling

### 5.3 `task_orchestrator`
- task admission, state transitions, dispatch coordination, escalation hooks

### 5.4 `policy_runtime_integration`
- OPA client, request normalization, fail-closed wrapper

### 5.5 `budget_runtime`
- reservation adapter, threshold-state evaluation, budget ledger coordination

### 5.6 `llm_gateway`
- routing-profile resolution, provider calls, fallback, usage normalization

### 5.7 `communication_gateway`
- A2A validation, ACP transport, retry and dead-letter handling

### 5.8 `execution_sandbox`
- sandbox enforcement, tool invocation, artifact/output capture

### 5.9 `data_access`
- repositories, transaction boundaries, outbox writes, checkpoints
 - project-document pointer/hash persistence for file-backed runtime docs

### 5.10 `observability`
- logs, traces, metrics, audit-event write boundary

### 5.11 `project_document_store` (runtime file boundary)
- canonical root: `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/`
- stores rich-text project docs (proposal/charter/metric plans/etc.)
- out-of-repo runtime storage only; source tree is never used for generated project files
- all writes are policy-gated and synchronized with DB pointer/hash metadata

## 6. Runnable Apps and Process Topology
Runnable apps:
- `api_app`
- `orchestrator_worker`
- `communication_worker`
- `admin_cli`

Hosting rules:
- `api_app` hosts `control_plane`, query read models, and ingress identity middleware.
- `orchestrator_worker` hosts `task_orchestrator`, `policy_runtime_integration`, `budget_runtime`, `execution_sandbox`, and `llm_gateway` client boundaries.
- `communication_worker` hosts `communication_gateway` retry, ack, and dead-letter loops.
- `admin_cli` hosts migration, seed, smoke, and diagnostics commands.

Budget runtime decision:
- `budget_runtime` is a runtime module hosted inside `orchestrator_worker` in v1.
- It is not a separate deployable process or container in `phase_0_local_first`.
- This keeps the runtime topology small while preserving the Define-stage budget contract.

Supporting infrastructure:
- `postgres`
- `redis`
- `opa`
- `otel_collector`
- `prometheus`
- `tempo`
- `loki`
- `grafana`
- externalized `litellm`

Startup order:
1. `postgres`
2. `redis`
3. `opa`
4. `litellm`
5. `otel_collector`
6. `prometheus`, `tempo`, `loki`, `grafana`
7. `api_app`
8. `orchestrator_worker`
9. `communication_worker`
10. `admin_cli` one-shot commands

## 7. Local Docker Compose Posture
Compose should support:
- deterministic startup ordering
- health checks
- env-file based config injection
- profile-based startup groups

Recommended profiles:
- `core`
- `obs`
- `full`

`full` is the design-signoff baseline.

## 8. Process Ownership Rules
- `api_app` handles ingress and request admission only
- `orchestrator_worker` owns task business transitions and governed dispatch decisions
- `communication_worker` owns retries and dead-letter behavior
- `admin_cli` owns migrations, seed/bootstrap, and diagnostics
- `governance/project services` own project-state transitions:
  - `proposed -> approved -> active -> paused -> completed -> terminated -> archived`

## 9. Related Follow-Ups
- foundation details live in `design/v1/foundation/ImplementationFoundation-v1.md`
- framework details live in `design/v1/foundation/ImplementationFrameworkSelection-v1.md`
- container topology lives in `design/v1/architecture/ContainerizationAndLocalInfraTopology-v1.md`
- quality and delivery details live in `implementation/v1/quality/QualityAndDelivery-v1.md`
