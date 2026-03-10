# OpenQilin v1 - Implementation Architecture

## 1. Scope
- Define the top-level implementation structure for the repo.
- Consolidate package layout, module dependency rules, and runnable app topology.

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
- `runtime modules -> observability` for telemetry/audit emission only

Forbidden:
- `shared_kernel -> feature modules`
- direct control-plane calls to sandbox/tool/provider execution
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

### 5.10 `observability`
- logs, traces, metrics, audit-event write boundary

## 6. Runnable Apps and Process Topology
Runnable apps:
- `api_app`
- `orchestrator_worker`
- `communication_worker`
- `admin_cli`

Supporting infrastructure:
- `postgres`
- `redis`
- `opa`
- `otel_collector`
- `grafana`
- selected trace/log backends
- optional externalized `litellm`

Startup order:
1. `postgres`
2. `redis`
3. `opa`
4. `otel_collector`
5. local observability backends
6. `api_app`
7. `orchestrator_worker`
8. `communication_worker`

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

## 8. Process Ownership Rules
- `api_app` handles ingress and request admission only
- `orchestrator_worker` owns task business transitions
- `communication_worker` owns retries and dead-letter behavior
- `admin_cli` owns migrations, seed/bootstrap, and diagnostics

## 9. Future Evolution
Possible later changes:
- split modules into separate deployable packages
- adopt a workspace if dependency isolation becomes necessary
- add Kubernetes/deployment manifests in later phases

## 10. Related Follow-Ups
- foundation details live in `design/v1/foundation/ImplementationFoundation-v1.md`
- quality and delivery details live in `design/v1/quality/QualityAndDelivery-v1.md`
