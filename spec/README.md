# OpenQilin - Specification Index

Purpose: implementation-level specifications for AI engineering agents.

## Taxonomy

### 1. Observability
- `spec/observability/SystemLogs.md`
- `spec/observability/AgentTracing.md`
- `spec/observability/MetricsAndAlerts.md`
- `spec/observability/AuditEvents.md`

### 2. Governance
- `spec/governance/architecture/GovernanceArchitecture.md`
- `spec/governance/architecture/AgentAuthorityGraph.md`
- `spec/governance/roles/SecretaryRoleContract.md`
- `spec/governance/roles/AdministratorRoleContract.md`
- `spec/governance/roles/AuditorRoleContract.md`
- `spec/governance/roles/CeoRoleContract.md`
- `spec/governance/roles/CwoRoleContract.md`
- `spec/governance/roles/CsoRoleContract.md`
- `spec/governance/roles/ProjectManagerRoleContract.md`
- `spec/governance/roles/DomainLeadRoleContract.md`
- `spec/governance/roles/SpecialistRoleContract.md`
- `spec/governance/architecture/EscalationModel.md`
- `spec/governance/architecture/SafetyDoctrine.md`
- `spec/governance/architecture/DecisionReviewGates.md`

### 3. Constitution
- `spec/constitution/ConstitutionManagement.md`
- `spec/constitution/PolicyVersioningAndChangeControl.md`
- `spec/constitution/ConstitutionBindingModel.md`
- `spec/constitution/PolicyEngineContract.md`
- `spec/constitution/BudgetEngineContract.md`

### 4. Orchestration
- `spec/orchestration/communication/OwnerInteractionModel.md`
- `spec/orchestration/registry/AgentRegistry.md`
- `spec/orchestration/registry/SkillCatalogAndBindings.md`
- `spec/orchestration/communication/AgentCommunicationA2A.md`
- `spec/orchestration/communication/AgentCommunicationACP.md`
- `spec/orchestration/memory/AgentMemoryModel.md`
- `spec/orchestration/memory/ProjectArtifactModel.md`
- `spec/orchestration/control/AgentLifecycleManagement.md`
- `spec/orchestration/registry/ToolRegistry.md`
- `spec/orchestration/control/TaskOrchestrator.md`

### 5. State Machines
- `spec/state-machines/AgentStateMachine.md`
- `spec/state-machines/ProjectStateMachine.md`
- `spec/state-machines/MilestoneStateMachine.md`
- `spec/state-machines/TaskStateMachine.md`
- `spec/state-machines/MemoryStateMachine.md`
- `spec/state-machines/CommunicationStateMachine.md`
- `spec/state-machines/EventStateMachine.md`

### 6. Infrastructure
- `spec/infrastructure/architecture/RuntimeArchitecture.md`
- `spec/infrastructure/architecture/DataModelAndSchemas.md`
- `spec/infrastructure/architecture/LlmGatewayContract.md`
- `spec/infrastructure/data/ArtifactIngestionAndExtraction.md`
- `spec/infrastructure/operations/DataMemoryOperationsPlaybooks.md`
- `spec/infrastructure/operations/DeploymentTopologyAndOps.md`
- `spec/infrastructure/security/ExecutionSandbox.md`
- `spec/infrastructure/data/StorageAndRetention.md`
- `spec/infrastructure/operations/FailureAndRecoveryModel.md`

### 7. Cross-Cutting
- `spec/cross-cutting/runtime/ErrorCodesAndHandling.md`
- `spec/cross-cutting/security/IdentityAndAccessModel.md`
- `spec/cross-cutting/security/DiscordOwnerChannelIdentityHardening.md`
- `spec/cross-cutting/conformance/ConformanceTestPlan.md`
- `spec/cross-cutting/conformance/RuleIdCatalog.md`
- `spec/cross-cutting/conformance/RuleRegistry.json`
- `spec/cross-cutting/conformance/ConformanceCoverage.json`
- `spec/cross-cutting/contracts/ProjectTaskQueryContracts.md`
- `spec/cross-cutting/conformance/SpecConstitutionReleaseChecklist.md`
- `spec/cross-cutting/planning/DeferredCapabilityActivationCriteria.md`
- `spec/cross-cutting/conformance/DocumentationTemplateAdoption.md`
- `spec/cross-cutting/reference/Glossary.md`

### 8. RFC Spikes
- `spec/rfcs/RFC-Process.md`
- `spec/rfcs/RFC-01-Orchestration-Governance-ControlPlane.md`
- `spec/rfcs/RFC-02-Memory-Intelligence-Observability.md`
- `spec/rfcs/RFC-03-Language-Runtime-Persistence-Deployment.md`
- `spec/rfcs/RFC-04-Data-Memory-Architecture.md`
- `spec/rfcs/RFC-05-Deployment-and-Cost-Strategy.md`
- `spec/rfcs/RFC-06-Project-Task-Status-And-Work-Artifact-Management.md`

### 9. Templates
- `spec/templates/ImplementationContractTemplate.md`
- `spec/templates/RoleContractTemplate.md`

## Precedence
1. `constitution/`
2. `spec/`
3. `docs/`

## Quality Gates
- Validate internal spec/constitution path references before merge.
- Ensure `spec/cross-cutting/conformance/RuleRegistry.json` and `spec/cross-cutting/conformance/ConformanceCoverage.json` are updated whenever rule IDs or rule tables change.
