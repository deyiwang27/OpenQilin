# OpenQilin v1 - Design Review Checklist and Exit Criteria

## 1. Scope
- Define design acceptance checklist for implementation handoff.
- Define exit criteria for moving from Design to Implementation.
- Provide traceability from `design/` artifacts to authoritative `spec/` contracts.

Precedence:
1. `constitution/`
2. `spec/`
3. `design/`

## 2. Design Acceptance Checklist
Each item must be `pass` before implementation kickoff.

### 2.1 Governance-Core Correctness
- `CHK-GOV-001`: No execution path bypasses policy authorization.
- `CHK-GOV-002`: State-changing uncertainty is fail-closed (policy, budget, sandbox, mandatory audit append).
- `CHK-GOV-003`: Obligation handling order is deterministic and documented.
- `CHK-GOV-004`: Escalation and enforcement paths are traceable and auditable.

### 2.2 Interface and Contract Completeness
- `CHK-INT-001`: Control-plane API surface is defined for owner commands, query contracts, and governance actions.
- `CHK-INT-002`: Request/response envelopes include required trace and policy metadata.
- `CHK-INT-003`: Error handling maps to canonical code families with retryability semantics.
- `CHK-INT-004`: Sync vs async boundaries are explicitly locked and consistent across docs.
- `CHK-INT-005`: LLM gateway routing profile and model-class mapping contracts are defined.

### 2.3 Reliability and Failure Behavior
- `CHK-REL-001`: A2A+ACP lifecycle defines retry, ack timeout, dead-letter, and idempotency behavior.
- `CHK-REL-002`: Message ordering guarantees are defined per channel type.
- `CHK-REL-003`: Timeout budgets per critical hop are defined and consistent.
- `CHK-REL-004`: Duplicate requests/messages are side-effect safe by idempotency design.

### 2.4 Data and Memory Readiness
- `CHK-DAT-001`: PostgreSQL package boundaries and source-of-record ownership are explicit.
- `CHK-DAT-002`: Redis responsibilities are bounded to non-authoritative roles.
- `CHK-DAT-003`: pgvector retrieval and rebuild semantics from source records are explicit.
- `CHK-DAT-004`: CDC replay/checkpoint recovery behavior is deterministic and auditable.

### 2.5 Observability and Operations Readiness
- `CHK-OBS-001`: Required span boundaries and correlation fields are documented.
- `CHK-OBS-002`: Minimum dashboard and alert set is defined with routing ownership.
- `CHK-OBS-003`: Governance-critical actions produce immutable audit evidence.
- `CHK-OBS-004`: Failure handling for collector/export/audit sink is defined.

### 2.6 Security and Identity Readiness
- `CHK-SEC-001`: External identity mapping and verification are fail-closed.
- `CHK-SEC-002`: Connector replay/idempotency controls are documented.
- `CHK-SEC-003`: Cross-project scope isolation is enforced in query/retrieval paths.

### 2.7 Implementation Hygiene
- `CHK-IMP-001`: No unresolved `TBD` or conflicting decision text in P0/P1 artifacts.
- `CHK-IMP-002`: Required conformance test scenarios are derivable from design artifacts.
- `CHK-IMP-003`: Operational playbook dependencies are identified for implementation planning.

## 3. Exit Criteria (Design -> Implementation)
All criteria are mandatory for design-stage exit:

1. `EXIT-001`: P0 and P1 design artifacts are completed and status-tracked in `design/TODO.txt`.
2. `EXIT-002`: This checklist is completed with no blocking failed item.
3. `EXIT-003`: Traceability matrix (Section 4) has no unmapped design artifact.
4. `EXIT-004`: Timeout/retry/idempotency semantics are internally consistent across ADR, sequence, and component docs.
5. `EXIT-005`: Core observability evidence requirements are defined for implementation verification.
6. `EXIT-006`: No unresolved contradiction with `constitution/` and `spec/` authoritative contracts.

## 4. Design-to-Spec Traceability Matrix
| Design artifact | Primary intent | Authoritative `spec/` contracts |
| --- | --- | --- |
| `design/v1/adr/ADR-0001-Runtime-Boundary-and-Service-Topology.md` | service boundaries and sync/async topology | `spec/architecture/ArchitectureBaseline-v1.md`, `spec/infrastructure/architecture/RuntimeArchitecture.md`, `spec/orchestration/control/TaskOrchestrator.md`, `spec/orchestration/communication/AgentCommunicationA2A.md`, `spec/orchestration/communication/AgentCommunicationACP.md` |
| `design/v1/adr/ADR-0002-Policy-and-Orchestration-Decision-Path.md` | governance-core decision path and fail-closed gates | `spec/constitution/PolicyEngineContract.md`, `spec/constitution/BudgetEngineContract.md`, `spec/orchestration/control/TaskOrchestrator.md`, `spec/cross-cutting/runtime/ErrorCodesAndHandling.md`, `spec/observability/AuditEvents.md` |
| `design/v1/adr/ADR-0003-A2A-ACP-Reliability-Pipeline.md` | reliability lifecycle, retries, dead-letter, ordering, idempotency | `spec/orchestration/communication/AgentCommunicationA2A.md`, `spec/orchestration/communication/AgentCommunicationACP.md`, `spec/state-machines/CommunicationStateMachine.md`, `spec/cross-cutting/runtime/ErrorCodesAndHandling.md` |
| `design/v1/sequences/SEQ-0001-Owner-Command-Policy-Budget-Sandbox.md` | normal governed execution path | `spec/orchestration/communication/OwnerInteractionModel.md`, `spec/orchestration/control/TaskOrchestrator.md`, `spec/constitution/PolicyEngineContract.md`, `spec/constitution/BudgetEngineContract.md` |
| `design/v1/sequences/SEQ-0002-Fail-Closed-and-Timeout-Branches.md` | critical failure branches and timeouts | `spec/cross-cutting/runtime/ErrorCodesAndHandling.md`, `spec/orchestration/control/TaskOrchestrator.md`, `spec/infrastructure/architecture/RuntimeArchitecture.md` |
| `design/v1/sequences/SEQ-0003-A2A-ACP-Reliability-Lifecycle.md` | transport delivery state transitions and dead-letter outcomes | `spec/orchestration/communication/AgentCommunicationA2A.md`, `spec/orchestration/communication/AgentCommunicationACP.md`, `spec/state-machines/CommunicationStateMachine.md` |
| `design/v1/components/ControlPlaneComponentDesign-v1.md` | control-plane API contracts and identity/auth integration | `spec/orchestration/communication/OwnerInteractionModel.md`, `spec/cross-cutting/security/IdentityAndAccessModel.md`, `spec/cross-cutting/security/DiscordOwnerChannelIdentityHardening.md`, `spec/cross-cutting/contracts/ProjectTaskQueryContracts.md`, `spec/orchestration/control/TaskOrchestrator.md` |
| `design/v1/data/DataAndMemoryComponentDesign-v1.md` | data boundaries, redis strategy, pgvector and CDC design | `spec/infrastructure/architecture/DataModelAndSchemas.md`, `spec/orchestration/memory/AgentMemoryModel.md`, `spec/orchestration/memory/ProjectArtifactModel.md`, `spec/infrastructure/data/ArtifactIngestionAndExtraction.md`, `spec/infrastructure/data/StorageAndRetention.md`, `spec/state-machines/MemoryStateMachine.md` |
| `design/v1/components/ObservabilityComponentDesign-v1.md` | OTel/Grafana pipeline, correlation, alerts | `spec/observability/ObservabilityArchitecture.md`, `spec/observability/MetricsAndAlerts.md`, `spec/observability/SystemLogs.md`, `spec/observability/AgentTracing.md`, `spec/observability/AuditEvents.md` |
| `design/v1/components/LlmGatewayComponentDesign-v1.md` | llm gateway routing, fallback, and model profile integration | `spec/infrastructure/architecture/LlmGatewayContract.md`, `spec/infrastructure/architecture/LlmModelRoutingProfile-v1.md`, `spec/constitution/BudgetEngineContract.md`, `spec/cross-cutting/runtime/ErrorCodesAndHandling.md` |

## 5. Required Handoff Evidence
- Approved design artifacts (P0/P1/P2) present in repository.
- Review record per artifact with reviewer/date/status.
- Implementation backlog seeds linked to design sections:
  - control-plane API and identity middleware tasks
  - data schema migration tasks
  - communication reliability and dedupe tasks
  - observability pipeline and dashboard provisioning tasks
- Conformance test coverage outline mapped to key rule families (`RT`, `POL`, `BUD`, `A2A`, `ACP`, `OBS`, `MET`, `LOG`, `SCHEMA`, `MEM`, `STR`).

## 6. Kickoff Decision Record
Implementation kickoff decision values:
- `go`: all checklist and exit criteria passed.
- `conditional_go`: minor non-blocking docs gaps, no governance/risk blockers.
- `no_go`: any blocker in governance-core correctness, reliability, or security readiness.

Current design-stage decision (2026-03-10):
- `go` for v1 implementation kickoff, subject to implementation-phase conformance testing.
