# OpenQilin - RFC 05: Deployment and Cost Strategy

## 1. Scope
Domains in this RFC:
- Local/dev deployment baseline with Docker
- Cloud deployment strategy for early-stage cost efficiency
- Runtime topology choices for control plane, workers, data, and observability
- Managed vs self-hosted boundaries for PostgreSQL/Redis/observability
- Backup, recovery, security, and cost-control baseline

Timebox:
- Spike (documentation and architecture decision only)
- Date: 2026-03-09

## 2. Investigation Questions
- What Docker topology should be the mandatory local/dev baseline (single-command reproducibility)?
- What cloud pattern is most cost-efficient in early stage: single-node, hybrid, or full managed?
- Which components should be managed vs self-hosted to minimize spend without unacceptable reliability risk?
- What minimum backup/recovery and secret-management requirements are needed before production?
- What trigger points should move OpenQilin from low-cost baseline to HA architecture?
- How should telemetry/dashboard retention and topology be configured for predictable cost?

## 3. Candidate Evaluation Matrix
| Domain | Candidate | Decision | Confidence | Conformance Impact | Notes |
| --- | --- | --- | --- | --- | --- |
| local/dev packaging | Docker Compose | adopt (mandatory baseline) | high | strong positive | Multi-container reproducibility with one compose model across dev/test/CI. |
| cloud runtime topology | single VM self-host all | adopt_later (POC only) | medium | neutral | Lowest absolute spend, but higher operational and recovery risk. |
| cloud runtime topology | hybrid single-region (recommended) | adopt (v1 production baseline) | high | strong positive | Stateless/runtime on one container host; managed PostgreSQL; controlled ops burden. |
| cloud runtime topology | full managed multi-node | adopt_later | medium | positive | Better reliability and operations at higher steady cost; use when scale/SLO demands. |
| database hosting | managed PostgreSQL | adopt (cloud production baseline) | high | strong positive | Automated backup/PITR reduces critical data risk and ops load. |
| cache/queue hosting | self-hosted Redis | adopt (v1 baseline) | medium-high | positive | Bounded role and low cost; move to managed at higher reliability needs. |
| cache/queue hosting | managed Redis | adopt_later | medium | positive | Better failover/ops, higher monthly fixed cost. |
| observability hosting | OTel Collector + Grafana OSS self-host | adopt (v1 baseline) | high | positive | Required observability at controllable cost; right-size later. |
| observability hosting | managed observability suite | adopt_later | medium | neutral-positive | Reduces ops, may raise telemetry storage/ingestion spend. |
| secrets management | secret manager / secure parameter store | adopt (cloud baseline) | high | strong positive | Removes hardcoded secrets and supports rotation. |
| cost controls | budget guardrails + scale triggers | adopt | high | strong positive | Aligns with governance-first and budget policy model. |

## 4. Target Use Cases
- Local single-machine reproducible development.
- Small early-stage cloud deployment with limited budget and moderate uptime expectations.
- Governance-critical AI runtime where policy/audit cannot be sacrificed for minimal cost.
- Clear upgrade path from low-cost deployment to resilient multi-node architecture.

## 5. Spike Findings and Decisions

### 5.1 Local and CI Baseline: Docker Compose
Decision:
- Adopt Docker Compose as mandatory local/dev baseline.

Why:
- Compose is explicitly designed for multi-container applications and works across development/testing/CI environments.
- Compose features needed by OpenQilin are available in one model: services, volumes, secrets, startup ordering, and profiles.

Required baseline patterns:
- `docker compose up` as first-class bring-up path.
- Volumes for persistent state.
- `depends_on` + `healthcheck` (`service_healthy`) for startup ordering.
- Compose secrets instead of plain env vars for sensitive values.
- Profiles to control optional components (e.g., heavier observability).

### 5.2 Cloud Strategy: Hybrid Single-Region Baseline (Recommended)
Decision:
- Adopt hybrid single-region architecture as v1 cloud baseline.

Recommended topology (v1):
- One container host (VM/instance):
  - FastAPI control plane + orchestrator workers
  - Redis (bounded cache/idempotency role)
  - OpenTelemetry Collector
  - Grafana OSS
- Managed PostgreSQL service:
  - automated backups enabled
  - PITR capability
- Object storage for backup artifacts/snapshots

Why this balance:
- Cheaper and simpler than full multi-node managed stack.
- Safer than self-hosting every critical component, because PostgreSQL durability/recovery is highest-risk domain.

### 5.3 Managed vs Self-Hosted Boundaries
Database:
- Managed PostgreSQL is recommended baseline for cloud production.
- Rationale: automated backups, retention-based restore, PITR are first-class managed capabilities.

Redis:
- Self-host Redis in v1 baseline is acceptable due bounded role.
- Must enable persistence strategy aligned to data-loss tolerance.
- Move to managed Redis when failover/SLO requirements increase.

Observability:
- Start with self-host OTel Collector + Grafana OSS.
- OTel collector supports agent/gateway deployment patterns and can be evolved as topology grows.
- Move to managed observability if team capacity/operational burden becomes limiting.

### 5.4 Security and Secrets Baseline
Decision:
- Adopt external secrets store for cloud credentials and API keys.

Minimum controls:
- No hardcoded secrets in source or compose files.
- Use managed secret/secure parameter service with encryption.
- Rotation policy for DB/API credentials.
- TLS termination at edge/proxy layer.
- Restricted network exposure (only required ingress ports).

### 5.5 Backup and Recovery Baseline
PostgreSQL baseline:
- Automated backups + retention.
- PITR-capable restore path.
- Quarterly restore drills.

Redis baseline:
- Persistence mode explicitly configured (RDB/AOF based on tolerance).
- Snapshot/backup schedule for any state you cannot recompute.

Artifact and config baseline:
- Backup runtime configuration and critical compose/provisioning artifacts.
- Keep infrastructure and observability provisioning in version control.

## 6. Cost Profile and Tradeoffs

### Option A: Single VM Self-Hosted Everything
Pros:
- Lowest absolute monthly cost.
- Fastest setup.

Cons:
- Highest operational and recovery risk.
- Backup, failover, and upgrade burden on the team.

Use when:
- POC/internal non-critical stages only.

### Option B: Hybrid Single-Region (Recommended)
Pros:
- Strong cost-efficiency/risk balance.
- Moves hardest durability problem (PostgreSQL) to managed service.
- Keeps most components inexpensive and controllable.

Cons:
- Still some ops overhead for Redis/observability host.

Use when:
- Early production with moderate SLO and tight budget.

### Option C: Full Managed / Multi-Node
Pros:
- Best reliability and operational continuity.
- Easier horizontal scale.

Cons:
- Highest fixed cost.
- More platform complexity/contracts.

Use when:
- Growth/SLO/compliance requires stronger availability guarantees.

## 7. Scaling Triggers and Upgrade Path
Upgrade from Option B to C when any 2 of the following persist:
- API/worker node sustained >70% CPU or memory pressure causing throttling.
- P95 request latency or job lag breaches SLO for 2+ consecutive review windows.
- Redis cache instance becomes single-point risk for operational continuity.
- Observability ingestion/retention cost exceeds planned budget threshold.
- Business requires lower RTO/RPO than single-host runtime can provide.

Upgrade sequence:
1. Split runtime into 2+ app/worker nodes behind load balancer.
2. Move Redis to managed HA (or replicated self-managed cluster).
3. Move Grafana DB backend to managed Postgres/MySQL if needed for HA.
4. Introduce OTel gateway tier for multi-node telemetry routing.

## 8. Migration and Rollback Notes
- Keep deployment interface container-based (`compose`/container image contracts) so runtime can shift from single host to orchestrated platform without app-level contract rewrite.
- If managed DB migration introduces instability, rollback by preserving logical/physical backup and cutover via read-only window.
- If managed observability spend is excessive, retain OTel collector pipeline and redirect exporters back to self-hosted stack.

## 9. Recommendation Summary
Adopt now:
- Docker Compose as local/dev/CI baseline.
- Hybrid cloud baseline (single runtime host + managed PostgreSQL).
- Self-hosted Redis (bounded role) for v1.
- Self-hosted OTel Collector + Grafana OSS baseline.
- External secret management and credential rotation.

Adopt later:
- Managed Redis.
- Managed observability stack.
- Multi-node/full-managed runtime topology.

Defer:
- Full managed multi-node as default from day one.

## 10. Sources (Primary)
- Docker Compose overview: https://docs.docker.com/compose/
- Compose file/spec reference: https://docs.docker.com/reference/compose-file/
- Compose startup order and health checks: https://docs.docker.com/compose/how-tos/startup-order/
- Compose secrets: https://docs.docker.com/compose/how-tos/use-secrets/
- Docker volumes: https://docs.docker.com/engine/storage/volumes/
- Docker restart policies: https://docs.docker.com/engine/containers/start-containers-automatically/
- Docker build cache optimization (CI): https://docs.docker.com/build/cache/optimize/

- FastAPI deployment concepts: https://fastapi.tiangolo.com/deployment/concepts/
- FastAPI Docker deployment guidance: https://fastapi.tiangolo.com/deployment/docker/
- Uvicorn deployment notes: https://www.uvicorn.org/deployment/

- PostgreSQL PITR / continuous archiving: https://www.postgresql.org/docs/current/continuous-archiving.html
- PostgreSQL base backup tool: https://www.postgresql.org/docs/current/app-pgbasebackup.html
- PostgreSQL row-level security: https://www.postgresql.org/docs/current/ddl-rowsecurity.html

- Redis persistence: https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/
- Redis replication: https://redis.io/docs/latest/operate/oss_and_stack/management/replication/

- OpenTelemetry Collector overview: https://opentelemetry.io/docs/collector/
- OpenTelemetry Collector deployment patterns: https://opentelemetry.io/docs/collector/deploy/
- OTel agent pattern: https://opentelemetry.io/docs/collector/deploy/agent/
- OTel gateway pattern: https://opentelemetry.io/docs/collector/deploy/gateway/

- Grafana installation/sizing/database guidance: https://grafana.com/docs/grafana/latest/setup-grafana/installation/
- Grafana configuration (`[database]`): https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/
- Grafana alerting contact points: https://grafana.com/docs/grafana/latest/alerting/fundamentals/notifications/contact-points/
- Grafana provisioning: https://grafana.com/docs/grafana/latest/administration/provisioning/

- AWS RDS automated backups + PITR model: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html
- AWS RDS enabling automated backups: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.Enabling.html
- Amazon ElastiCache snapshots/backups: https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/backups.html
- AWS Secrets Manager intro: https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html
- AWS Systems Manager Parameter Store: https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html
- AWS Well-Architected Cost Optimization pillar: https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html

## 11. Evidence Strength Notes
- High confidence: Docker-based local baseline, PostgreSQL backup/recovery requirements, Redis persistence tradeoffs, OTel/Grafana deployment patterns.
- Medium confidence: exact cloud provider cost crossover between hybrid and full-managed options (provider/region specific and changes over time).
- Inference note: the recommended hybrid topology is an architectural synthesis from reliability and cost-optimization guidance, aligned with current OpenQilin governance-first constraints.
