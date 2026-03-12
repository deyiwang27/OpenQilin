# OpenQilin - v1 Architecture Baseline

## 1. Purpose and Scope
- This document locks the v1 implementation baseline for OpenQilin.
- It maps selected technologies to runtime components and authoritative interfaces.
- It is the implementation kickoff reference for the next technical-design phase.

Normative precedence:
1. `constitution/`
2. `spec/`
3. `design/` (working design artifacts in next phase)
4. `docs/`

## 2. Baseline Decision Snapshot
| Domain | v1 Baseline Decision | Source |
| --- | --- | --- |
| Core runtime language | Python | `spec/rfcs/RFC-03-Language-Runtime-Persistence-Deployment.md` |
| Control plane API | FastAPI | `spec/rfcs/RFC-01-Orchestration-Governance-ControlPlane.md` |
| Orchestration engine | LangGraph | `spec/rfcs/RFC-01-Orchestration-Governance-ControlPlane.md` |
| Policy decision point | OPA (fail-closed) | `spec/rfcs/RFC-01-Orchestration-Governance-ControlPlane.md` |
| Agent communication payload | A2A | `spec/orchestration/communication/AgentCommunicationA2A.md` |
| Agent communication transport | ACP | `spec/orchestration/communication/AgentCommunicationACP.md` |
| Tool connectivity | MCP/FastMCP | `spec/rfcs/RFC-01-Orchestration-Governance-ControlPlane.md` |
| Tool governance wrapper | Skills registry/bindings | `spec/orchestration/registry/SkillCatalogAndBindings.md` |
| LLM gateway | LiteLLM | `spec/rfcs/RFC-02-Memory-Intelligence-Observability.md` |
| Source-of-record data store | PostgreSQL | `spec/rfcs/RFC-04-Data-Memory-Architecture.md` |
| Vector retrieval | pgvector (PostgreSQL co-located) | `spec/rfcs/RFC-04-Data-Memory-Architecture.md` |
| Hot-path cache/idempotency | Redis (bounded role) | `spec/rfcs/RFC-04-Data-Memory-Architecture.md` |
| Assistive memory overlay | Mem0 (defer/adopt_later) | `spec/cross-cutting/planning/DeferredCapabilityActivationCriteria.md` |
| Telemetry baseline | OpenTelemetry + Grafana | `spec/rfcs/RFC-02-Memory-Intelligence-Observability.md` |
| Observability overlays | LangSmith + AgentOps (retained) | `spec/rfcs/RFC-02-Memory-Intelligence-Observability.md` |
| Deployment path | local-first with Docker, then cloud hybrid promotion | `spec/rfcs/RFC-05-Deployment-and-Cost-Strategy.md` |
| Owner interface posture | Discord-first + Grafana, React/TypeScript defer | `spec/rfcs/RFC-03-Language-Runtime-Persistence-Deployment.md` |
| Owner chat governance posture | fixed Discord chat classes with state-driven project-channel membership; `secretary` participation defined as pending in first MVP | `spec/orchestration/communication/OwnerInteractionModel.md` |

## 3. Runtime Component Map
### 3.1 Governance and Control Plane
- `owner_channel_adapter`:
  - primary: Discord connector (v1)
  - responsibility: ingress normalization, identity binding, trace initialization
  - enforces contract-defined owner chat classes and membership constraints before governed ingress
- `control_plane_api` (FastAPI):
  - authoritative API boundary for commands, queries, and governed actions
  - exposes stable contracts to any non-core adapters
- `policy_runtime` (OPA + constitution bundle):
  - authoritative allow/deny/obligation decision point
  - fail-closed on load/eval errors
- `task_orchestrator` (LangGraph-backed):
  - executes governed state transitions, dispatch sequencing, escalation hooks

### 3.2 Communication and Tool Plane
- `a2a_contract`:
  - canonical inter-agent payload envelope
  - authority/policy metadata required per message
- `acp_transport`:
  - runtime wire contract for ack/retry/dead-letter behavior
- `tool_plane`:
  - MCP/FastMCP for tool invocation transport/discovery
  - skill registry as policy-governed capability mapping

### 3.3 Data, Memory, and Retrieval Plane
- `postgresql`:
  - authoritative state: project/task/milestone/agent/event
  - registry + governance/audit supporting entities
  - relational and JSONB models
- `project_document_store`:
  - file-backed rich-text project documentation under `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/`
  - out-of-repo runtime storage only; never under source tree
  - pointer/hash synchronization with relational metadata is required
  - strict MVP document-type enum and cap policy (including total active-doc cap) is enforced fail-closed
- `pgvector`:
  - embedding index co-located with Postgres data model
- `redis`:
  - cache, idempotency, and bounded async coordination only
- `mem0`:
  - optional assistive memory overlay (not source-of-record)

### 3.4 Observability Plane
- `otel_collector`:
  - required telemetry ingest and routing backbone
- `grafana`:
  - required dashboards and alert routing
- `langsmith`:
  - LLM trace and evaluation overlay
- `agentops`:
  - operational/cost analytics overlay

## 4. Authoritative v1 Interfaces
### 4.1 `policy`
- Request/response authority: `spec/constitution/PolicyEngineContract.md`
- Constitution binding and version behavior: `spec/constitution/ConstitutionBindingModel.md`

### 4.2 `task`
- Runtime sequencing and gate order: `spec/orchestration/control/TaskOrchestrator.md`
- State transition authority:
  - `spec/state-machines/TaskStateMachine.md`
  - `spec/state-machines/ProjectStateMachine.md`
  - `spec/state-machines/MilestoneStateMachine.md`
  - `spec/state-machines/AgentStateMachine.md`

Project lifecycle lock (v1):
- `proposed -> approved -> active -> paused -> completed -> terminated -> archived`
- no separate `rejected` project state in first MVP; proposal revisions remain in `proposed`

### 4.3 `a2a+acp`
- Envelope contract: `spec/orchestration/communication/AgentCommunicationA2A.md`
- Transport/reliability contract: `spec/orchestration/communication/AgentCommunicationACP.md`
- Owner chat-class and membership contract: `spec/orchestration/communication/OwnerInteractionModel.md`
- Discord identity/channel hardening controls: `spec/cross-cutting/security/DiscordOwnerChannelIdentityHardening.md`

### 4.4 `llm_gateway`
- Runtime boundary: `spec/infrastructure/architecture/LlmGatewayContract.md`
- Routing profile and model catalog: `spec/infrastructure/architecture/LlmModelRoutingProfile-v1.md`
- Governance budget/policy coupling: `spec/constitution/BudgetEngineContract.md`

### 4.5 `memory`
- Agent memory model: `spec/orchestration/memory/AgentMemoryModel.md`
- Project/task artifact model: `spec/orchestration/memory/ProjectArtifactModel.md`
- Query contract boundary: `spec/cross-cutting/contracts/ProjectTaskQueryContracts.md`

### 4.6 `audit`
- Event model: `spec/observability/AuditEvents.md`
- Trace and error correlation:
  - `spec/observability/AgentTracing.md`
  - `spec/cross-cutting/runtime/ErrorCodesAndHandling.md`

## 5. Deployment Baseline (v1)
Phase model:
- `phase_0_local_first`:
  - Docker-first local/dev reproducibility
  - governance-core conformance and recovery drill gating
- `phase_1_cloud_hybrid`:
  - single-region hybrid topology after phase_0 gates
  - managed PostgreSQL preferred for cloud durability

Reference:
- `constitution/domain/OperationsPolicy.yaml`
- `spec/infrastructure/operations/DeploymentTopologyAndOps.md`

## 6. Deferred/Optional Capabilities
Deferred unless explicit activation criteria are met:
- Custom React/TypeScript admin console
- WhatsApp owner channel
- Mem0 as active memory path
- Managed Redis
- Full multi-node managed deployment topology

Activation criteria source:
- `spec/cross-cutting/planning/DeferredCapabilityActivationCriteria.md`

## 7. Implementation Kickoff Gates
Before feature implementation begins:
1. Constitution active version + bundle hash aligned with version snapshot.
2. Rule registry and conformance coverage artifacts refreshed.
3. Interface specs referenced in Section 4 are treated as implementation contracts.
4. No unresolved contradictions between `constitution/` and `spec/` for v1 decisions.

## 8. Non-Goals for Baseline
- This document does not replace detailed component design documents.
- This document does not define sprint-level execution planning.
- This document does not add new constitutional policy semantics.
