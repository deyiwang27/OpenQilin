# OpenQilin - Deployment Topology and Operations Specification

## 1. Scope
- Defines deployment topology and operational controls for local-first and cloud phases.
- Defines minimum production-readiness gates for backup, restore, secrets, and observability.

## 2. Deployment Strategy
- `phase_0_local_first`:
  - local Docker Compose deployment is mandatory baseline.
  - governance-core conformance checks must pass before cloud promotion.
- `phase_1_cloud_hybrid`:
  - cloud rollout uses hybrid single-region topology.
  - managed PostgreSQL with backup and PITR capability is required.

## 3. Local Baseline (Phase 0)
Mandatory services:
- control plane API/runtime
- task orchestration workers
- policy engine runtime
- budget engine runtime hosted inside the task orchestration worker process in v1
- Redis
- PostgreSQL (local profile)
- OpenTelemetry Collector
- Grafana and compatible local telemetry backends

Local baseline requirements:
- single-command startup (`docker compose up` profile)
- health checks and deterministic startup ordering
- reproducible seed/config for test environments

## 4. Cloud Baseline (Phase 1)
Cloud hybrid topology:
- one runtime host for stateless services and worker pool
- managed PostgreSQL service
- self-host Redis initially (bounded role)
- self-host OTel Collector + Grafana initially

Cloud baseline requirements:
- managed secrets store for runtime credentials
- encrypted transport and restricted ingress
- backup schedule and restore test evidence

## 5. Scaling and Evolution
Move beyond cloud baseline when sustained signals are observed:
- CPU/memory pressure affecting throughput or latency
- repeated queue lag/backlog breaches
- resilience targets require lower RTO/RPO than single runtime host

Evolution path:
1. split runtime across multiple app and worker nodes
2. move Redis to managed HA tier
3. externalize budget runtime or sandbox pools only if isolation or scale requires it
4. evolve observability from single-host to gateway and managed pattern

## 6. Operational Control Set
Mandatory controls:
- backup retention policy for data stores
- periodic restore drills
- secret rotation policy
- incident alert routing and on-call ownership
- immutable audit and conformance evidence retention

## 7. Contract Alignment
- Runtime behavior must remain aligned with:
  - `spec/infrastructure/architecture/RuntimeArchitecture.md`
  - `spec/infrastructure/operations/FailureAndRecoveryModel.md`
  - `spec/constitution/BudgetEngineContract.md`
- Communication posture remains A2A + ACP in runtime.

## 8. Conformance Checks
- Local baseline starts and passes smoke checks deterministically.
- Cloud promotion blocked if restore drill evidence is missing.
- Deployment metadata includes policy and build provenance references.
- Secrets are referenced externally and never committed in plaintext.
