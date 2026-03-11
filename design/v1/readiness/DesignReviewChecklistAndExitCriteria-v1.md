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
- `CHK-SEC-003`: Cross-project scope isolation is enforced in query and retrieval paths.

### 2.7 Implementation Hygiene
- `CHK-IMP-001`: No unresolved `TBD` or conflicting decision text in P0/P1 artifacts.
- `CHK-IMP-002`: Required conformance test scenarios are derivable from design artifacts.
- `CHK-IMP-003`: Operational playbook dependencies are identified for implementation planning.
- `CHK-IMP-004`: Planning authority between live tracker and backlog reference is explicit.

## 3. Exit Criteria (Design -> Implementation)
All criteria are mandatory for design-stage exit:

1. `EXIT-001`: P0, P1, and P2 design artifacts are completed and status-tracked in `design/TODO.txt`.
2. `EXIT-002`: This checklist is completed with no blocking failed item.
3. `EXIT-003`: Traceability matrix (Section 4) has no unmapped design artifact.
4. `EXIT-004`: Timeout, retry, idempotency, and hosting semantics are internally consistent across ADR, sequence, component, and implementation-planning docs.
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
| `design/v1/components/TaskOrchestratorComponentDesign-v1.md` | orchestrator admission, state management, and downstream dispatch boundaries | `spec/orchestration/control/TaskOrchestrator.md`, `spec/state-machines/TaskStateMachine.md`, `spec/governance/architecture/EscalationModel.md`, `spec/constitution/PolicyEngineContract.md`, `spec/constitution/BudgetEngineContract.md` |
| `design/v1/components/PolicyRuntimeIntegrationDesign-v1.md` | policy request normalization and fail-closed integration | `spec/constitution/PolicyEngineContract.md`, `spec/constitution/ConstitutionBindingModel.md`, `spec/cross-cutting/runtime/ErrorCodesAndHandling.md` |
| `design/v1/components/CommunicationGatewayComponentDesign-v1.md` | A2A and ACP producer-consumer runtime and dead-letter handling | `spec/orchestration/communication/AgentCommunicationA2A.md`, `spec/orchestration/communication/AgentCommunicationACP.md`, `spec/state-machines/CommunicationStateMachine.md`, `spec/cross-cutting/runtime/ErrorCodesAndHandling.md` |
| `design/v1/components/ExecutionSandboxAndToolPlaneDesign-v1.md` | sandbox enforcement, tool registry, and skill-binding runtime | `spec/infrastructure/security/ExecutionSandbox.md`, `spec/orchestration/registry/SkillCatalogAndBindings.md`, `spec/orchestration/registry/ToolRegistry.md`, `spec/orchestration/registry/AgentRegistry.md` |
| `design/v1/data/DataAndMemoryComponentDesign-v1.md` | data boundaries, Redis strategy, pgvector and CDC design | `spec/infrastructure/architecture/DataModelAndSchemas.md`, `spec/orchestration/memory/AgentMemoryModel.md`, `spec/orchestration/memory/ProjectArtifactModel.md`, `spec/infrastructure/data/ArtifactIngestionAndExtraction.md`, `spec/infrastructure/data/StorageAndRetention.md`, `spec/state-machines/MemoryStateMachine.md` |
| `design/v1/components/ObservabilityComponentDesign-v1.md` | OTel and Grafana pipeline, correlation, alerts | `spec/observability/ObservabilityArchitecture.md`, `spec/observability/MetricsAndAlerts.md`, `spec/observability/SystemLogs.md`, `spec/observability/AgentTracing.md`, `spec/observability/AuditEvents.md` |
| `design/v1/components/LlmGatewayComponentDesign-v1.md` | llm gateway routing, fallback, and model profile integration | `spec/infrastructure/architecture/LlmGatewayContract.md`, `spec/infrastructure/architecture/LlmModelRoutingProfile-v1.md`, `spec/constitution/BudgetEngineContract.md`, `spec/cross-cutting/runtime/ErrorCodesAndHandling.md` |
| `design/v1/foundation/ImplementationFoundation-v1.md` | toolchain, prerequisites, configuration, and bootstrap posture | `spec/infrastructure/operations/DeploymentTopologyAndOps.md`, `spec/infrastructure/operations/FailureAndRecoveryModel.md`, `spec/infrastructure/architecture/RuntimeArchitecture.md` |
| `design/v1/foundation/ImplementationFrameworkSelection-v1.md` | baseline Python library and framework selection | `spec/architecture/ArchitectureBaseline-v1.md`, `spec/infrastructure/architecture/RuntimeArchitecture.md` |
| `implementation/v1/workflow/DeveloperWorkflowAndContributionGuide-v1.md` | developer contribution, local run, and merge workflow | `spec/infrastructure/operations/DeploymentTopologyAndOps.md`, `spec/cross-cutting/conformance/ConformanceTestPlan.md` |
| `design/v1/architecture/ImplementationArchitecture-v1.md` | repo layout, module map, hosting topology | `spec/architecture/ArchitectureBaseline-v1.md`, `spec/infrastructure/architecture/RuntimeArchitecture.md`, `spec/infrastructure/operations/DeploymentTopologyAndOps.md` |
| `design/v1/architecture/ContainerizationAndLocalInfraTopology-v1.md` | local container topology and mandatory signoff stack | `spec/infrastructure/operations/DeploymentTopologyAndOps.md`, `spec/observability/ObservabilityArchitecture.md` |
| `design/v1/architecture/ControlPlaneModuleDesign-v1.md` | implementation package split for control-plane runtime | `spec/orchestration/communication/OwnerInteractionModel.md`, `spec/cross-cutting/contracts/ProjectTaskQueryContracts.md`, `spec/cross-cutting/runtime/ErrorCodesAndHandling.md` |
| `design/v1/architecture/TaskOrchestratorModuleDesign-v1.md` | implementation package split for orchestration runtime | `spec/orchestration/control/TaskOrchestrator.md`, `spec/state-machines/TaskStateMachine.md` |
| `design/v1/architecture/PolicyBudgetIntegrationModuleDesign-v1.md` | implementation package split and hosting for policy and budget runtime modules | `spec/constitution/PolicyEngineContract.md`, `spec/constitution/BudgetEngineContract.md`, `spec/infrastructure/operations/DeploymentTopologyAndOps.md` |
| `design/v1/architecture/CommunicationGatewayModuleDesign-v1.md` | implementation package split for communication delivery runtime | `spec/orchestration/communication/AgentCommunicationA2A.md`, `spec/orchestration/communication/AgentCommunicationACP.md`, `spec/state-machines/CommunicationStateMachine.md` |
| `design/v1/architecture/ExecutionSandboxToolPlaneModuleDesign-v1.md` | implementation package split for sandbox and tool-plane runtime | `spec/infrastructure/security/ExecutionSandbox.md`, `spec/orchestration/registry/SkillCatalogAndBindings.md`, `spec/orchestration/registry/ToolRegistry.md` |
| `design/v1/architecture/LlmGatewayModuleDesign-v1.md` | implementation package split for llm gateway runtime | `spec/infrastructure/architecture/LlmGatewayContract.md`, `spec/infrastructure/architecture/LlmModelRoutingProfile-v1.md` |
| `design/v1/architecture/DataAccessModuleDesign-v1.md` | implementation package split for persistence, outbox, and cache layers | `spec/infrastructure/architecture/DataModelAndSchemas.md`, `spec/infrastructure/data/StorageAndRetention.md` |
| `design/v1/architecture/ObservabilityModuleDesign-v1.md` | implementation package split for logs, traces, metrics, alerts, and audit append | `spec/observability/ObservabilityArchitecture.md`, `spec/observability/AuditEvents.md` |
| `implementation/v1/quality/QualityAndDelivery-v1.md` | test strategy, CI gates, and release posture | `spec/cross-cutting/conformance/ConformanceTestPlan.md`, `spec/infrastructure/operations/DeploymentTopologyAndOps.md` |
| `implementation/v1/quality/ReleaseVersioningAndRollback-v1.md` | release packaging, versioning, and rollback rules | `spec/infrastructure/operations/DeploymentTopologyAndOps.md`, `spec/infrastructure/operations/FailureAndRecoveryModel.md` |
| `implementation/v1/planning/ImplementationBacklogSeed-v1.md` | stable workstream and delivery-order reference | `spec/architecture/ArchitectureBaseline-v1.md`, `spec/cross-cutting/conformance/ConformanceTestPlan.md` |
| `implementation/v1/planning/ImplementationMilestones-v1.md` | milestone sequencing and first executable slice | `spec/architecture/ArchitectureBaseline-v1.md`, `spec/cross-cutting/conformance/ConformanceTestPlan.md` |
| `design/v1/readiness/DesignReviewChecklistAndExitCriteria-v1.md` | design exit criteria and cross-artifact traceability | `spec/architecture/ArchitectureBaseline-v1.md`, `spec/cross-cutting/conformance/ConformanceTestPlan.md` |
| `design/v1/readiness/DesignReviewRecord-v1.md` | design-stage review evidence and kickoff decision | `spec/architecture/ArchitectureBaseline-v1.md`, `spec/cross-cutting/conformance/ConformanceTestPlan.md` |

## 5. Required Handoff Evidence
- Approved design artifacts (P0, P1, P2) present in repository.
- Review record present:
  - `design/v1/readiness/DesignReviewRecord-v1.md`
- Implementation backlog seeds linked to design sections:
  - `implementation/v1/planning/ImplementationBacklogSeed-v1.md`
  - `design/TODO.txt` as the design-stage historical tracker
- Conformance test coverage outline mapped to key rule families (`RT`, `POL`, `BUD`, `A2A`, `ACP`, `OBS`, `MET`, `LOG`, `SCHEMA`, `MEM`, `STR`).

## 6. Kickoff Decision Record
Implementation kickoff decision values:
- `go`: all checklist and exit criteria passed.
- `conditional_go`: minor non-blocking docs gaps, no governance-risk blockers.
- `no_go`: any blocker in governance-core correctness, reliability, or security readiness.

Current design-stage decision (2026-03-10):
- `go` for v1 implementation kickoff.
- rationale:
  - design backlog is closed
  - implementation-planning hosting and topology decisions are explicit
  - design-stage tracking authority and implementation-tracking boundary are explicit
