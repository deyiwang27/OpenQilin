# OpenQilin v1 - Containerization and Local Infrastructure Topology

## 1. Scope
- Define the Docker-level runtime topology for local-first v1 implementation.
- Clarify mandatory versus optional services for development, CI, and design-signoff testing.

## 2. Topology Decision
v1 local-first topology:
- application processes run in dedicated containers
- infrastructure dependencies run in dedicated containers
- `budget_runtime` is not a separate container; it is a module hosted inside `orchestrator_worker`
- Kubernetes is out of scope for initial v1 implementation and testing

## 3. Application Containers
| Service | Purpose | Mandatory |
| --- | --- | --- |
| `api` | FastAPI ingress and query API | yes |
| `orchestrator` | task orchestration, policy/budget integration, sandbox/llm dispatch coordination | yes |
| `communication` | ACP delivery, retries, dead-letter handling | yes |
| `admin` | migrations, seed, smoke commands | yes, as one-shot task |
| `litellm` | provider routing proxy for Gemini and future models | yes for LLM-backed flows |

Implementation note:
- `execution_sandbox` runs as a governed module inside `orchestrator` for v1, using local process isolation on the worker host.

## 4. Infrastructure Containers
| Service | Purpose | Mandatory |
| --- | --- | --- |
| `postgres` | source-of-record relational storage | yes |
| `redis` | idempotency, cache, coordination | yes |
| `opa` | policy engine runtime | yes |
| `otel-collector` | telemetry ingestion and routing | yes |
| `prometheus` | metrics backend for Grafana | yes for signoff/full profile |
| `tempo` | trace backend | yes for signoff/full profile |
| `loki` | log backend | yes for signoff/full profile |
| `grafana` | dashboards and alert visualization | yes for signoff/full profile |

## 5. Compose Profiles
### 5.1 `core`
For day-to-day feature development:
- `api`
- `orchestrator`
- `communication`
- `admin` on demand
- `postgres`
- `redis`
- `opa`
- `litellm`

### 5.2 `obs`
Adds the observability stack:
- `otel-collector`
- `prometheus`
- `tempo`
- `loki`
- `grafana`

### 5.3 `full`
Design-signoff and end-to-end profile:
- `core`
- `obs`

Rule:
- `full` is the mandatory profile for implementation readiness and conformance smoke validation.
- `core` is a developer convenience profile, not the authoritative readiness baseline.

## 6. Startup Order
1. `postgres`
2. `redis`
3. `opa`
4. `litellm`
5. `otel-collector`
6. `prometheus`, `tempo`, `loki`, `grafana`
7. `api`
8. `orchestrator`
9. `communication`
10. `admin` one-shot tasks (`migrate`, `seed`, `smoke`)

## 7. Authoritative Local Bring-Up Contract
This document is the authoritative source for local full-stack bring-up.

Readiness rule:
- the stack is considered `up` only when long-running services are healthy and the `admin bootstrap` one-shot flow has completed successfully

Canonical full-stack sequence:
1. `docker compose --profile full up -d`
2. `docker compose run --rm admin bootstrap`
3. verify health and smoke output from the bootstrap command

Required `admin bootstrap` behavior in implementation:
- run forward migrations
- seed deterministic baseline data
- run minimum smoke checks against `api`, `orchestrator`, and `communication`
- exit non-zero on any failed prerequisite or smoke check

Interpretation of the spec's single-command startup baseline:
- `docker compose --profile full up -d` is the single command that starts the long-running baseline
- `admin bootstrap` is the required one-shot readiness gate that makes the started stack usable for end-to-end development and tests
- developers may use the lighter `core` profile during feature work, but `full + admin bootstrap` is the only authoritative design-signoff path

## 8. Network and Secret Posture
- Services communicate over a private Compose network.
- No plaintext secrets are committed; runtime secrets come from env files excluded from version control.
- Only `api` exposes inbound ports by default.
- Grafana exposure is local-only in `phase_0_local_first`.
- Provider credentials are injected only into `litellm` and components that strictly require them.

## 9. CI Posture
CI baseline:
- use containerized `postgres`, `redis`, `opa`, and `litellm`
- observability backends may be slimmed for fast PR runs, but `otel-collector` stays in scope for telemetry wiring checks
- full-stack smoke runs use the `full` topology and `admin bootstrap` readiness gate before release/promote gates

## 10. Manual Preparation Steps
You still need to do these outside the repo:
1. Install Docker Desktop or equivalent Docker + Compose runtime.
2. Confirm Docker has enough CPU and memory for Postgres, Redis, OPA, and Grafana stack together.
3. Create local env files with Gemini and Discord credentials.
4. Verify ports used by Postgres, Redis, Grafana, and API are free.

## 11. Future Evolution
Deferred beyond v1 initial implementation:
- Kubernetes manifests and Helm charts
- separate sandbox host/container pool
- separate budget runtime service if isolation or scale requires it

## 12. Related Design Artifacts
- `design/v1/foundation/ImplementationFoundation-v1.md`
- `design/v1/architecture/ImplementationArchitecture-v1.md`
- `implementation/v1/workflow/DeveloperWorkflowAndContributionGuide-v1.md`
- `design/v1/components/ObservabilityComponentDesign-v1.md`
