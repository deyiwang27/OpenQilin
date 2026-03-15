# OpenQilin v2 Planning Artifacts

Status: `active — MVP-v2 kickoff approved`
Updated: `2026-03-15`

---

## How to Read This

**Start here for execution:** `05-milestones/MvpV2MilestonePlan-v1.md` — official milestone plan with WP index and bug fix map.

**For each milestone:** Read the corresponding WP document in `05-milestones/`. WPs contain actionable task checklists, entry criteria, and done criteria.

**For design and implementation guidance:** See `design/v2/` — ADRs, component deltas, and per-milestone module designs.

---

## Structure

### `05-milestones` — Official Milestone Plan (start here)

| Document | Content |
|---|---|
| [MvpV2MilestonePlan-v1.md](05-milestones/MvpV2MilestonePlan-v1.md) | Master milestone plan: overview table, sequencing rationale, bug fix map, WP index |
| [M11-WorkPackages-v1.md](05-milestones/M11-WorkPackages-v1.md) | M11: Grammar layer, Secretary activation, C-7 fix, LangSmith env wiring |
| [M12-WorkPackages-v1.md](05-milestones/M12-WorkPackages-v1.md) | M12: OPA wiring, obligation dispatcher, PostgreSQL migration, Redis, OTel, security fixes, CSO activation |
| [M13-WorkPackages-v1.md](05-milestones/M13-WorkPackages-v1.md) | M13: LangGraph adoption, project space binding, DL activation, loop controls, H-3 fix, sandbox scaffolding |
| [M14-WorkPackages-v1.md](05-milestones/M14-WorkPackages-v1.md) | M14: PostgreSQL budget ledger, token cost model, budget obligation, Grafana dashboard, alerting |
| [M15-WorkPackages-v1.md](05-milestones/M15-WorkPackages-v1.md) | M15: RuntimeSettings singleton, conversation persistence, idempotency namespace, doctor CLI, loop/cost audit |
| [M16-WorkPackages-v1.md](05-milestones/M16-WorkPackages-v1.md) | M16: README, roadmap, demo, contributor path, website, sponsorship readiness |

### Progress Tracker

| Document | Content |
|---|---|
| [ImplementationProgress-v2.md](ImplementationProgress-v2.md) | In-repo WP/milestone status mirror; bug fix tracking table |

### `00-direction` — Direction and Success Criteria (reference)

| Document | Content | Status |
|---|---|---|
| [MvpV2SuccessCriteria-v1.md](00-direction/MvpV2SuccessCriteria-v1.md) | MVP-v2 success bar, major objectives, completion criteria | **active reference** |
| [MvpV2ArchitectureDelta-v1.md](00-direction/MvpV2ArchitectureDelta-v1.md) | Keep/refactor/replace/defer view of the v1→v2 delta | **active reference** |
| [ArchitecturalReviewFindings-v2.md](00-direction/ArchitecturalReviewFindings-v2.md) | Exhaustive finding/bug list with file/line references and severity | **active reference** |
| [archive/TemporaryMvpPlan-v2.md](00-direction/archive/TemporaryMvpPlan-v2.md) | Original direction draft | superseded by `05-milestones/MvpV2MilestonePlan-v1.md` |

### `01-product` — Product Strategy (reference)

| Document | Content |
|---|---|
| [SolopreneurRequirementAlignment-v1.md](01-product/SolopreneurRequirementAlignment-v1.md) | Market-informed alignment to the solopreneur ICP |
| [SolopreneurCoreWorkflows-v1.md](01-product/SolopreneurCoreWorkflows-v1.md) | Core workflows MVP-v2 must do well |
| [OperatorVisibilityModel-v1.md](01-product/OperatorVisibilityModel-v1.md) | Dashboard and operator visibility model |
| [ChatSurfaceStrategy-v1.md](01-product/ChatSurfaceStrategy-v1.md) | Discord-now / adapter-ready-later surface strategy |
| [AgentNamingAndPersonaStrategy-v1.md](01-product/AgentNamingAndPersonaStrategy-v1.md) | Institutional agent naming and persona approach |

### `02-architecture` — Architecture Decisions (reference)

| Document | Content |
|---|---|
| [ProjectSpaceBindingModel-v1.md](02-architecture/ProjectSpaceBindingModel-v1.md) | Runtime binding model for project spaces |
| [LlmProfileBindingModel-v2.md](02-architecture/LlmProfileBindingModel-v2.md) | LLM profile system, role bindings, and overrides |
| [ToolAndSkillRegistryStrategy-v1.md](02-architecture/ToolAndSkillRegistryStrategy-v1.md) | Governed tool and skill registry strategy |

### `03-community` — Community and Funding Strategy (active — M16 inputs)

| Document | Content |
|---|---|
| [OpenSourceCommunityStrategy-v1.md](03-community/OpenSourceCommunityStrategy-v1.md) | Open-source positioning, public introduction, community contribution |
| [FundingAndSponsorshipStrategy-v1.md](03-community/FundingAndSponsorshipStrategy-v1.md) | Startup credits, GitHub Sponsors, sponsorship readiness |

### `04-research` — Research Spikes (reference)

| Document | Content |
|---|---|
| [OpenClawSpikeReport-v1.md](04-research/OpenClawSpikeReport-v1.md) | OpenClaw comparison spike |
| [OpenClawReferenceLearningReport-v1.md](04-research/OpenClawReferenceLearningReport-v1.md) | Adopt/adapt/reject learning from OpenClaw |
| [EdictSpikeReport-v1.md](04-research/EdictSpikeReport-v1.md) | Edict comparison spike |
| [ExternalReferenceLandscapeSpike-v1.md](04-research/ExternalReferenceLandscapeSpike-v1.md) | External reference landscape scan |
| [ZeroClawSpikeReport-v1.md](04-research/ZeroClawSpikeReport-v1.md) | ZeroClaw comparison spike — 3 adopt findings deferred post-MVP |

---

## Design Artifacts

Implementation guidance lives in `design/v2/`, not here. For each milestone:

| Milestone | Design docs |
|---|---|
| M11 | `design/v2/architecture/M11-DiscordGrammarAndSecretaryModuleDesign-v2.md`, `design/v2/components/ControlPlaneComponentDelta-v2.md` |
| M12 | `design/v2/architecture/M12-InfrastructureWiringAndSecurityModuleDesign-v2.md`, `design/v2/adr/ADR-0004`, `design/v2/adr/ADR-0006`, `design/v2/components/PolicyRuntimeComponentDelta-v2.md` |
| M13 | `design/v2/architecture/M13-ProjectSpaceAndOrchestrationModuleDesign-v2.md`, `design/v2/adr/ADR-0005`, `design/v2/components/OrchestratorComponentDelta-v2.md` |
| M14 | `design/v2/architecture/M14-BudgetAndDashboardModuleDesign-v2.md`, `design/v2/adr/ADR-0007`, `design/v2/components/BudgetRuntimeComponentDelta-v2.md` |
| M15 | `design/v2/architecture/M15-RuntimePolishModuleDesign-v2.md` |

---

## Milestone Completion Protocol

A milestone is complete when:
1. All WPs in the milestone's WP document are marked `done`.
2. All WP done-criteria pass in a full compose stack (no InMemory substitutes).
3. Integration tests cover the critical path added in the milestone.
4. No new `InMemory*` placeholder introduced in a production code path.
5. The milestone exit criteria are demonstrably met.
