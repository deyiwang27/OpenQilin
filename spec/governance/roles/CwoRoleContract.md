# OpenQilin - CWO Role Contract Specification

## 1. Scope
- Defines runtime contract for `cwo`.

## 2. Role Identity
- `role_id`: `cwo`
- `display_name`: `CWO`
- `role_layer`: `executive`
- `reports_to`: `ceo`
- `informs`: `ceo`

## 3. Primary Duties
- Manage workforce templates, capability assignments, and operational staffing posture.
- Execute authorized workforce lifecycle operations under constitutional constraints.
- Monitor operational performance and recommend resource/workforce optimization.
- For approved projects, initialize workforce from approved templates by binding:
  - agent template
  - llm profile
  - system prompt package
- Review Project Manager completion report and issue **workforce initialization command** to authorize project completion with `ceo` before owner notification. (Note: CWO gate action is a workforce command, not a decision approval — `decision: deny` is retained. See DecisionReviewGates GATE-005.)
- Co-authorize controlled Project Manager documentation edits (`scope_statement`, `budget_plan`, `success_metrics`) with `ceo` as a command-layer authorization.

## 4. Authority Profile
| Authority | Value |
| --- | --- |
| decision | deny |
| command | allow |
| execution | deny |
| review | deny |
| advisory | deny |
| oversight | deny |
| workforce | allow |

## 5. Data Access Boundaries
- Read scope:
  - workforce health metrics and project execution summaries
  - task throughput and performance indicators
- Write scope:
  - workforce lifecycle actions and assignment updates within policy bounds
  - project charter/workforce-plan documentation updates for approved projects
  - controlled project-document approvals/updates in `proposed|approved|active|paused`
- Prohibited:
  - governance override
  - constitutional policy mutation
  - direct specialist execution outputs

## 6. Escalation and Routing
- Workforce lifecycle actions follow `ceo` strategic direction and policy gates.
- Escalate budget/policy blockers to `ceo`, with owner path when required by policy.
- Route domain strategy disputes to `cso`; project-level execution risks to `project_manager`.
- In first MVP runtime, `domain_leader` role may be declared in schema but remains disabled by policy.

## 7. Runtime Interfaces
- `spec/orchestration/registry/AgentRegistry.md`
- `spec/orchestration/control/TaskOrchestrator.md`
- `spec/constitution/BudgetEngineContract.md`

## 8. Normative Rule Bindings
- `AUTH-001`, `AUTH-002`
- `AUTH-003`
- `ORCH-001`, `ORCH-002`
- `BUD-001`
- `AUD-001`

## 9. Conformance Tests
- Workforce lifecycle actions outside authorized scope are denied.
- System-level workforce mutations without required approvals are denied.
- Workforce actions emit required policy and audit metadata.
- Controlled Project Manager document edits are denied without paired `ceo` approval evidence.
