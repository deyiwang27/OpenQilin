# OpenQilin v1 - App Entrypoints and Process Topology

## 1. Scope
- Define runnable app entrypoints for v1.
- Define process ownership and startup order for local-first deployment.
- Align local runtime composition with Docker Compose baseline.

## 2. v1 Runnable Apps
### 2.1 `api_app`
Purpose:
- owner ingress, query contracts, governance mutation ingress

Primary module owner:
- `control_plane`

### 2.2 `orchestrator_worker`
Purpose:
- task admission, state machine execution, policy/budget dispatch coordination

Primary module owner:
- `task_orchestrator`

### 2.3 `communication_worker`
Purpose:
- A2A/ACP delivery, retries, DLQ handling, delivery callbacks

Primary module owner:
- `communication_gateway`

### 2.4 `admin_cli`
Purpose:
- migrations, seed/bootstrap, diagnostics, recovery helpers

Primary module owners:
- `data_access`
- ops/bootstrap tooling

## 3. Supporting Infrastructure Services
Mandatory local services:
- `postgres`
- `redis`
- `opa`
- `otel_collector`
- `grafana`
- trace/log backing services selected by observability design

Optional local service:
- `litellm` if not embedded or app-managed inside repo runtime

## 4. Startup Order
1. `postgres`
2. `redis`
3. `opa`
4. `otel_collector`
5. local observability backends
6. `api_app`
7. `orchestrator_worker`
8. `communication_worker`

`admin_cli` is on-demand and not part of steady-state startup.

## 5. Local Docker Compose Posture
Compose should support:
- single-command startup for full local baseline
- service health checks
- deterministic dependency ordering
- environment-file based local config injection
- profile-based optional services where helpful

Recommended compose profiles:
- `core`: api + orchestrator + postgres + redis + opa
- `obs`: collector + grafana + trace/log backends
- `full`: full local baseline

## 6. Process Ownership Rules
- `api_app` must not execute orchestration logic inline beyond admission/request handling
- `orchestrator_worker` owns task business transitions
- `communication_worker` owns retries and dead-letter handling
- only `admin_cli` should run migrations and seed/bootstrap commands

## 7. Failure and Restart Notes
- worker processes must tolerate dependent service restarts using fail-closed behavior where required
- restart ordering should preserve persistence services first, stateless processes second
- zero-context restart artifacts are owned by persistence and observability layers, not app entrypoints

## 8. Related Design Follow-Ups
- module boundaries are defined in `ModuleDependencyMap-v1.md`
- bootstrap steps are defined in `BootstrapAndMigrationWorkflow-v1.md`
- container details are defined later in `ContainerizationAndLocalInfraTopology-v1.md`
