# OpenQilin - Specification Index

Purpose: implementation-level specifications for AI engineering agents.

## Taxonomy

### 1. Observability
- `spec/observability/SystemLogs.md`
- `spec/observability/AgentTracing.md`
- `spec/observability/MetricsAndAlerts.md`
- `spec/observability/AuditEvents.md`

### 2. Governance
- `spec/governance/GovernanceArchitecture.md`
- `spec/governance/AgentAuthorityGraph.md`
- `spec/governance/EscalationModel.md`
- `spec/governance/SafetyDoctrine.md`
- `spec/governance/DecisionReviewGates.md`

### 3. Constitution
- `spec/constitution/ConstitutionManagement.md`
- `spec/constitution/PolicyVersioningAndChangeControl.md`
- `spec/constitution/ConstitutionBindingModel.md`
- `spec/constitution/PolicyEngineContract.md`
- `spec/constitution/BudgetEngineContract.md`

### 4. Orchestration
- `spec/orchestration/OwnerInteractionModel.md`
- `spec/orchestration/AgentRegistry.md`
- `spec/orchestration/AgentCommunicationA2A.md`
- `spec/orchestration/AgentCommunicationACP.md`
- `spec/orchestration/AgentMemoryModel.md`
- `spec/orchestration/AgentLifecycleManagement.md`
- `spec/orchestration/ToolRegistry.md`
- `spec/orchestration/TaskOrchestrator.md`

### 5. State Machines
- `spec/state-machines/AgentStateMachine.md`
- `spec/state-machines/ProjectStateMachine.md`
- `spec/state-machines/TaskStateMachine.md`
- `spec/state-machines/MemoryStateMachine.md`
- `spec/state-machines/CommunicationStateMachine.md`
- `spec/state-machines/EventStateMachine.md`

### 6. Infrastructure
- `spec/infrastructure/RuntimeArchitecture.md`
- `spec/infrastructure/DataModelAndSchemas.md`
- `spec/infrastructure/ExecutionSandbox.md`
- `spec/infrastructure/StorageAndRetention.md`
- `spec/infrastructure/FailureAndRecoveryModel.md`

### 7. Cross-Cutting
- `spec/cross-cutting/ErrorCodesAndHandling.md`
- `spec/cross-cutting/IdentityAndAccessModel.md`
- `spec/cross-cutting/ConformanceTestPlan.md`
- `spec/cross-cutting/RuleIdCatalog.md`
- `spec/cross-cutting/RuleRegistry.json`
- `spec/cross-cutting/ConformanceCoverage.json`
- `spec/cross-cutting/Glossary.md`

### 8. RFC Spikes
- `spec/rfcs/RFC-Process.md`
- `spec/rfcs/RFC-01-Orchestration-Governance-ControlPlane.md`
- `spec/rfcs/RFC-02-Memory-Intelligence-Observability.md`
- `spec/rfcs/RFC-03-Language-Runtime-Persistence-Deployment.md`

## Precedence
1. `constitution/`
2. `spec/`
3. `docs/`

## Quality Gates
- Run `python3 scripts/spec_integrity_check.py` before merge.
- Regenerate rule registry artifacts with `python3 scripts/generate_rule_registry.py` after rule updates.
