# OpenQilin - RFC 06: Project/Task Status and Work Artifact Management

## 1. Scope
This RFC investigates how to manage detailed project and task status when canonical state is in PostgreSQL, while preserving rich planning/execution context (objectives, pathways, risks, metrics, notes, requirements, TODOs, and role-authored docs).

Primary scenario:
- Owner discusses with `ceo`, `cwo`, `cso` to initiate a project.
- `cwo` creates `project_manager` and `domain_lead` agents.
- `project_manager` decomposes milestones/tasks and maintains planning notes.
- Specialist agents execute tasks with task-level requirements and updates.

## 2. Investigation Questions
- What should be strictly structured in PostgreSQL vs captured as narrative documents?
- Should project/task docs live in database, markdown files, or both?
- How do we keep narrative docs and structured status synchronized without ambiguity?
- How should milestone/task decomposition be represented for deterministic agent execution and auditing?
- How should agents read/write project/task context safely from PostgreSQL during execution?

## 3. Options Evaluated

### Option A: DB-Centric (Everything in PostgreSQL)
Model:
- Structured fields + JSONB text blobs + version tables in PostgreSQL.

Pros:
- Single transactional system for status + context.
- Strong consistency and RBAC/RLS controls.
- Easy joins for dashboards and policy checks.

Cons:
- Worse authoring UX for long-form collaborative documents.
- Harder Git-style review/change workflows for narrative artifacts.
- Narrative docs can become unstructured JSON dumping ground.

### Option B: Doc-Centric (Markdown/Git as Primary, DB as Index)
Model:
- Project/task docs in Markdown (Git), DB stores pointers/metadata.

Pros:
- Excellent review/version UX (PRs, branch protections, CODEOWNERS).
- Human-readable and portable.

Cons:
- Runtime status determinism weak if key state is only in docs.
- Sync complexity for agent runtime decisions.
- Harder to enforce strict state-machine transitions from free-text changes.

### Option C: Hybrid State + Artifact + Event (Recommended)
Model:
- PostgreSQL is authoritative for status/state and structured planning entities.
- Narrative artifacts are Markdown-first, but ingested/versioned in DB as governed artifacts.
- Event/outbox stream records every significant update.

Pros:
- Deterministic runtime/policy behavior from structured authoritative state.
- High-quality human collaboration on docs.
- Strong auditability and replayability.

Cons:
- More moving parts than single-store approaches.
- Requires clear contracts for artifact/state synchronization.

## 4. Recommended Approach
Adopt Option C: **Hybrid State + Artifact + Event**.

Core principle:
- **Status truth** lives in PostgreSQL state tables.
- **Context truth** lives in versioned artifacts (Markdown + DB-ingested version metadata/content).
- **History truth** lives in append-only events and immutable audit records.

This best matches OpenQilin governance requirements and your workflow.

## 5. Technical Solution Design

### 5.1 Data Domains
1. State domain (authoritative, structured)
- `project_container` (project root record)
- `milestone`
- `task`
- `task_assignment`
- `task_requirement`
- `project_metric`
- `project_risk`
- `project_objective`

2. Artifact domain (versioned narrative)
- `project_artifact`
- `project_artifact_version`
- `artifact_link` (project/milestone/task relation)

3. Event domain (append-only timeline)
- `status_event`
- `outbox_events`
- `audit_event`

### 5.2 Project/Task Artifact Types
Define explicit artifact types so agents know where to read/write:
- `project_charter` (owner + c-suite alignment)
- `project_strategy`
- `project_risk_register`
- `project_metric_plan`
- `milestone_plan`
- `task_brief`
- `task_execution_notes`
- `task_handover_report`
- `project_retrospective`

Each artifact version should include:
- `artifact_id`, `version_no`, `author_role`, `author_agent_id`
- `content_md`
- `summary_structured` (JSON)
- `change_reason`
- `trace_id`
- `created_at`

### 5.3 Lifecycle Flow
1. Project initiation (Owner + `ceo` + `cwo` + `cso`)
- Create `project_container` row in `proposed`.
- Generate `project_charter` artifact with objectives, pathways, risks, metrics.
- Parse and persist structured extracts into `project_objective`, `project_risk`, `project_metric`.
- Approval gate transitions project to `approved` / `active`.

2. Planning (`project_manager` + `domain_lead`)
- Create `milestone` tree and `task` rows.
- Attach `milestone_plan` and `task_brief` artifacts.
- Task requirements persisted in `task_requirement` (structured constraints and acceptance criteria).

3. Execution (specialist agents)
- Specialist reads `task_brief` + structured task fields.
- Writes progress to `status_event` and `task_execution_notes` artifacts.
- State transitions follow `TaskStateMachine` (`created` -> `queued` -> `authorized` ...).

4. Closure
- Generate `task_handover_report` and `project_retrospective` artifacts.
- Persist final metric evaluation and outcome summary.
- Archive artifact snapshots and keep immutable audit links.

### 5.4 Status Management Pattern
For detailed status, use three layers:
- Layer 1: canonical state columns (`project.state`, `task.state`).
- Layer 2: structured sub-status fields (e.g., `planning_status`, `risk_status`, `qa_status`, `blocked_reason_code`).
- Layer 3: narrative status in artifacts (`task_execution_notes`, decisions, rationale).

This avoids overloading a single status field while preserving machine readability.

### 5.5 Sync Pattern (Artifacts <-> Structured Fields)
- On artifact update, run extraction pipeline:
  - detect sections (`objectives`, `risks`, `metrics`, `requirements`)
  - write normalized rows/upserts
  - emit `status_event` and `outbox_events`
- On structured state change, append event and optionally regenerate artifact summary blocks.

Conflict rule:
- State-machine fields are DB-authoritative.
- Narrative artifacts cannot directly force illegal state transitions.

### 5.6 Agent Query Contract (PostgreSQL)
Agents should not run arbitrary SQL by default. Use query classes:
- `get_project_snapshot(project_id)`
- `get_milestone_plan(milestone_id)`
- `get_task_brief(task_id)`
- `get_task_runtime_context(task_id)`
- `append_task_note(task_id, content_md, trace_id)`

Enforcement:
- Role-scoped views + RLS.
- Sensitive reads audited.
- Mutations wrapped by policy and state-transition guards.

## 6. Suggested Schema Blueprint (Minimal)

### 6.1 Status Tables
- `project_container(project_id, state, planning_status, risk_status, metric_status, owner_agent_id, updated_at)`
- `milestone(milestone_id, project_id, state, due_at, sequence_no, updated_at)`
- `task(task_id, milestone_id, state, priority, assignee_agent_id, requirement_level, acceptance_criteria_json, updated_at)`

### 6.2 Artifact Tables
- `project_artifact(artifact_id, artifact_type, project_id, milestone_id, task_id, current_version, status, created_at)`
- `project_artifact_version(artifact_id, version_no, content_md, summary_structured_json, author_role, author_agent_id, change_reason, trace_id, created_at)`

### 6.3 Event Tables
- `status_event(event_id, aggregate_type, aggregate_id, from_state, to_state, reason_code, trace_id, actor_role, actor_id, created_at)`
- `audit_event(...)` (immutable envelope per governance specs)

## 7. Operational Guidance
- Use materialized read models for dashboards (project health, milestone burnup, blocked tasks).
- Keep append-only event history for replay/audit.
- Use Redis as cache for frequently-read snapshots, not as source-of-truth.
- Keep Mem0 optional for personalized memory augmentation; do not store authoritative project/task state in Mem0.

## 8. Risks and Mitigations
- Risk: document edits diverge from structured status.
- Mitigation: extraction+validation pipeline with conflict checks and required section schema.

- Risk: too much narrative data in task rows.
- Mitigation: enforce artifact boundary and keep task table strictly operational.

- Risk: agent writes bypass governance.
- Mitigation: write APIs enforce policy checks and state-machine guards; DB permissions deny direct unsafe writes.

## 9. Spec Outputs
- The following specs were added/updated from this RFC recommendation:
- `spec/orchestration/memory/ProjectArtifactModel.md` (artifact taxonomy + lifecycle)
- `spec/infrastructure/data/ArtifactIngestionAndExtraction.md` (markdown->structured sync contract)
- `spec/state-machines/MilestoneStateMachine.md` (currently implied by project/task only)
- `spec/cross-cutting/contracts/ProjectTaskQueryContracts.md` (agent-safe SQL contracts)

## 10. Recommendation Summary
For OpenQilin, use:
- PostgreSQL as authoritative status/state and structured planning store.
- Markdown artifacts for collaborative narrative context, with DB-ingested version tracking.
- Event/outbox timeline for audit/replay.

This provides the best balance of determinism, agent usability, governance, and collaboration.

## 11. Sources (Primary)
- PostgreSQL Row Security Policies: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- PostgreSQL Logical Decoding Concepts: https://www.postgresql.org/docs/current/logicaldecoding-explanation.html
- PostgreSQL Triggers Overview: https://www.postgresql.org/docs/current/trigger-definition.html
- PostgreSQL Materialized Views: https://www.postgresql.org/docs/current/rules-materializedviews.html
- PostgreSQL Generated Columns: https://www.postgresql.org/docs/current/ddl-generated-columns.html
- pgvector (official): https://github.com/pgvector/pgvector
- Redis Streams `XREADGROUP`: https://redis.io/docs/latest/commands/xreadgroup/
- Debezium PostgreSQL Connector: https://debezium.io/documentation/reference/stable/connectors/postgresql.html
- Debezium Outbox Event Router: https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html
- Mem0 Memory Types: https://docs.mem0.ai/core-concepts/memory-types
- Mem0 Entity-Scoped Memory: https://docs.mem0.ai/platform/features/entity-scoped-memory
- Mem0 Graph Memory: https://docs.mem0.ai/platform/features/graph-memory
- CommonMark: https://commonmark.org/
- CommonMark Spec: https://spec.commonmark.org/
- GitHub Issues (about/sub-issues/dependencies): https://docs.github.com/issues/tracking-your-work-with-issues/about-issues
- GitHub Projects fields: https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields
- GitHub Milestones progress: https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/viewing-your-milestones-progress
- GitHub linking PRs to issues: https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue
- GitHub Issue templates/forms: https://docs.github.com/articles/configuring-issue-templates-for-your-repository
- GitHub branch protection: https://docs.github.com/github/administering-a-repository/about-protected-branches

## 12. Evidence Strength Notes
- High confidence: PostgreSQL authoritative-state pattern, event/outbox approach, pgvector/Redis operational roles.
- Medium confidence: exact artifact extraction quality without a dedicated schema/validator implementation.
- Inference note: the recommended three-layer status pattern (state/sub-status/narrative artifact) is an architecture synthesis from the above sources and existing OpenQilin governance constraints.
