# M14 Work Packages — Executive and Operational Agent Activation

Milestone: `M14`
Status: `planned`
Entry gate: M13 complete (LangGraph active, project spaces wired, CSO correctly implemented, Secretary spec aligned)
Design ref: `spec/governance/roles/`, `spec/governance/architecture/DecisionReviewGates.md`, `spec/orchestration/control/TaskOrchestrator.md`

---

## Milestone Goal

Activate all remaining institutional and operational agents as real runtime participants: Project Manager, CEO, CWO, Auditor, Administrator, and Specialist. Wire the DecisionReviewGates proposal approval flow (CSO → CEO → CWO). All agents enforce their spec-defined authority profiles and data access boundaries.

---

## WP M14-01 — Project Manager Agent

**Goal:** Implement `ProjectManagerAgent` as the default handler in project channels. PM decomposes project goals, manages task state, writes project artifacts, dispatches to Specialist for execution, and escalates to Domain Leader for domain questions.

**Design ref:** `spec/governance/roles/ProjectManagerRoleContract.md`, `spec/orchestration/memory/ProjectArtifactModel.md`

**Entry criteria:** M13 complete (project-space routing active, LangGraph wired, DL agent exists for escalation target).

### Tasks

- [ ] Create `src/openqilin/agents/project_manager/` package: `agent.py`, `models.py`, `prompts.py`, `artifact_writer.py`
- [ ] Implement `ProjectManagerRequest` and `ProjectManagerResponse` in `models.py`:
  - Request: `message`, `intent`, `context` (with `project_id` required), `trace_id`
  - Response: `advisory_text`, `action_taken`, `routing_hint`, `artifact_updated`, `trace_id`
- [ ] Implement `ProjectManagerAgent.handle(request)`:
  - **NOTE: PM has `advisory: deny` — responses for DISCUSSION/QUERY are status reports and project decisions, not advisory text. Framing must be directives and status, not advice.**
  - `DISCUSSION`/`QUERY` → read project artifacts + task state; issue status report or project decision (not advisory)
  - `MUTATION` → validate authority; write execution artifacts within allowed types; task assignment dispatch
  - `ADMIN` → controlled document update path (requires CEO+CWO approval evidence); reject without approval
  - Project context required: reject request if `project_id` is absent
  - Enforce state-aware write: PM writes are only permitted when project state is `active`; reject artifact writes in any other project state
- [ ] Implement `artifact_writer.py` — `PMProjectArtifactWriter`:
  - Direct-write types (project state `active` only): `execution_plan`, `risk_register`, `decision_log`, `progress_report`
  - Append-only types: `progress_report` and `decision_log` entries are append-only (no in-place updates)
  - Conditional-write types (require CEO+CWO approval evidence): `scope_statement`, `budget_plan`, `success_metrics`
  - `completion_report` write: PM writes one `completion_report` when project reaches completion; append-only; required by CWO before co-approval review
  - All writes pass through `project_artifact_repo` with role=`project_manager` and `trace_id`
  - Enforce state-aware write contract: reject all writes when project state is not `active` (fail-closed)
  - Prohibited: `project_charter`, `workforce_plan`
- [ ] Implement Specialist dispatch: `dispatch_to_specialist(task_id, project_id)` — creates a task routed to `specialist` target via `task_dispatch_service`; PM cannot execute tasks directly
- [ ] Implement DL escalation: `escalate_to_domain_leader(question, project_id, trace_id)` — calls `DomainLeaderAgent.handle_escalation()` (from M13-WP5); synthesizes DL response into PM reply
- [ ] Implement budget risk escalation to CWO: when task budget state indicates risk, PM emits escalation event on "risk monitoring chain: project_manager → cwo" (EscalationModel §4, budget violations path)
- [ ] Wire `ProjectManagerAgent` in `dependencies.py`
- [ ] Add unit tests: PM handles discussion (returns status report, not advisory); PM dispatches specialist; PM rejects charter write; PM rejects admin without approval evidence; PM rejects artifact write when project state is not `active`; PM writes completion_report on project completion

### Outputs

- `ProjectManagerAgent` active as default handler in project channels
- Specialist dispatch and DL escalation wired
- Project artifact write authority enforced by role

### Done criteria

- [ ] Message in project channel → PM issues project status report or decision (not advisory text — PM has `advisory: deny`)
- [ ] PM dispatches specialist task: creates task with `target=specialist`
- [ ] PM rejects `project_charter` or `workforce_plan` write
- [ ] PM rejects controlled document edit without CEO+CWO approval evidence
- [ ] PM rejects any artifact write when project state is not `active` (state-aware write enforcement)
- [ ] PM writes `completion_report` when project completes; artifact is append-only
- [ ] PM budget risk escalation emits escalation event on the PM → CWO risk monitoring chain
- [ ] PM escalation to DL returns DL response synthesized into PM reply

---

## WP M14-02 — CEO Agent

**Goal:** Implement `CEOAgent` as the strategic decision authority. CEO approves/denies project proposals, co-approves project completion and controlled PM edits with CWO, and routes workforce intents to CWO and strategy questions to CSO.

**Design ref:** `spec/governance/roles/CeoRoleContract.md`, `spec/governance/architecture/DecisionReviewGates.md`

**Entry criteria:** WP M14-01 complete (PM active); WP M14-03 (CWO) may be developed in parallel.

### Tasks

- [ ] Create `src/openqilin/agents/ceo/` package: `agent.py`, `models.py`, `prompts.py`
- [ ] Implement `CeoRequest` and `CeoResponse` in `models.py`:
  - Request: `message`, `intent`, `context`, `proposal_id: str | None`, `cso_review_outcome: str | None`, `trace_id`
  - Response: `decision: str | None` (`approved`/`denied`/`needs_revision`), `advisory_text`, `routing_hint`, `trace_id`
- [ ] Implement `CeoAgent.handle(request)`:
  - **NOTE: CEO has `advisory: deny` — responses for DISCUSSION/QUERY are strategic directives and decisions, not advisory text. Route strategy questions to CSO; route workforce intents to CWO; CEO issues the directive response, not an advisory.**
  - `DISCUSSION`/`QUERY` → issue strategic directive; route strategy questions to CSO; route workforce to CWO
  - Project proposal review (`proposal_id` present): read CSO review outcome from `governance_artifacts`; GATE-005 check: block if no CSO review record exists; make `approved`/`denied`/`needs_revision` decision; emit governance decision record (GATE-004)
  - Track `revision_cycle_count` from the gate event record; after three unresolved `Strategic Conflict` cycles, require explicit override flag to proceed (GATE-003)
  - Co-approval: record CEO co-approval evidence for project completion and controlled PM document edits; enforce that CWO co-approval evidence must also exist before controlled PM doc edits go through
  - Decision authority: CEO decisions are persisted to `governance_artifacts` table with `trace_id` and rationale
- [ ] Implement `CeoDecisionWriter`: persists `decision_log` entries and governance records for CEO decisions; required for GATE-004 audit compliance; includes `revision_cycle_count` in gate event record
- [ ] Implement escalation routing: CSO for strategy questions; CWO for workforce intents; PM for project execution concerns; owner for structural/constitutional exceptions
- [ ] Wire `CeoAgent` in `dependencies.py`
- [ ] Add unit tests: CEO approves aligned proposal; CEO denies proposal without CSO review record (GATE-005); CEO records decision with audit trail (GATE-004); CEO routes workforce intent to CWO; CEO blocks controlled PM doc edit without CWO co-approval evidence (ORCH-005); third unresolved `Strategic Conflict` cycle blocks without override flag (GATE-003)

### Outputs

- `CeoAgent` active with decision and command authority
- Project proposal approval wired; decisions audit-logged
- GATE-004 compliance: CEO decisions recorded with rationale

### Done criteria

- [ ] CEO approves project proposal with CSO `Aligned` review → project advances to owner co-approval
- [ ] CEO denies proposal without recorded CSO review outcome → gate blocked (GATE-005)
- [ ] CEO decision persisted to governance records with `trace_id`, rationale, and `revision_cycle_count` (GATE-004)
- [ ] Third unresolved `Strategic Conflict` revision cycle blocked without explicit override flag (GATE-003)
- [ ] CEO routes workforce intent to CWO (not handled inline — CEO has `advisory: deny`)
- [ ] CEO routes strategy question to CSO (not handled inline)
- [ ] Controlled PM document edit without both CEO+CWO co-approval evidence → denied (ORCH-005)

---

## WP M14-03 — CWO Agent

**Goal:** Implement `CWOAgent` as the workforce lifecycle authority. CWO prepares workforce initialization packages, initializes workforce from approved templates, co-approves project completion and controlled PM edits with CEO, and routes domain strategy disputes to CSO.

**Design ref:** `spec/governance/roles/CwoRoleContract.md`, `spec/orchestration/registry/AgentRegistry.md`

**Entry criteria:** WP M14-01 complete (PM active); WP M14-02 (CEO) may be developed in parallel.

### Tasks

- [ ] Create `src/openqilin/agents/cwo/` package: `agent.py`, `models.py`, `prompts.py`, `workforce_initializer.py`
- [ ] Implement `CwoRequest` and `CwoResponse` in `models.py`:
  - Request: `message`, `intent`, `context`, `project_id: str | None`, `trace_id`
  - Response: `action_taken`, `advisory_text`, `workforce_status`, `trace_id`
- [ ] Implement `CwoAgent.handle(request)`:
  - **NOTE: CWO has `decision: deny` — CWO does not make decisions; it executes commands and manages workforce. "Co-approval" for CWO means CWO records its workforce-readiness authorization (a command action), while the approval decision belongs to CEO. Language in implementation must reflect command authority, not decision authority.**
  - Workforce lifecycle commands: bind `agent_template + llm_profile + system_prompt_package` to project on approval
  - Project proposal preparation: draft `workforce_plan` artifact for CWO submission into DecisionReviewGates flow; also draft `project_charter` artifact for approved projects (CWO is a `project_charter` co-owner per ProjectArtifactModel §3)
  - Co-approval: record CWO workforce-readiness authorization (command action) for project completion and controlled PM document edits
  - Read `completion_report` artifact written by PM before recording co-approval for project completion (spec §3: "Review Project Manager completion report")
  - Track `revision_cycle_count` on proposal resubmissions; relay count to CEO gate event record
  - Route domain strategy disputes to CSO; project execution risks to PM; budget/policy blockers to CEO
- [ ] Implement `workforce_initializer.py` — `WorkforceInitializer`:
  - `initialize_project_workforce(project_id, template)` — binds agent template, LLM profile, system prompt to project in agent registry; runs only after full approval chain evidence present (CSO record + CEO decision + owner co-approval)
  - Writes `workforce_plan` artifact with `author_role=cwo` and `trace_id`
  - Writes or co-authors `project_charter` artifact when not yet present (CWO is co-owner)
- [ ] Wire the full DecisionReviewGates proposal flow:
  - CWO drafts proposal → triggers CSO review request (calls `CSOAgent.handle` with `proposal_id`)
  - CSO returns review outcome (read from `governance_artifacts`) → CWO routes outcome + proposal to CEO for decision
  - CEO approves → owner co-approval → CWO calls `initialize_project_workforce()`
  - Gate blocked at any step: proposal remains in `proposed` state; reason recorded; `revision_cycle_count` incremented
- [ ] Wire `CwoAgent` in `dependencies.py`
- [ ] Add unit tests: CWO drafts proposal and triggers CSO review; CWO reads completion_report before recording co-approval; CWO initializes workforce after full approval chain completes; CWO rejects initialization without full approval evidence; CWO writes project_charter artifact

### Outputs

- `CWOAgent` active with command and workforce authority
- Full DecisionReviewGates flow wired (CSO → CEO → owner → CWO initialization)
- Workforce initialization conditioned on approval chain evidence

### Done criteria

- [ ] CWO drafts proposal → CSO review triggered → CEO review presented with CSO outcome
- [ ] CWO records workforce-readiness authorization (command action, not decision) for project completion only after reading PM `completion_report`
- [ ] CWO workforce initialization rejected without full approval chain evidence (CSO record + CEO decision + owner co-approval)
- [ ] Workforce plan artifact written with `trace_id` and `author_role=cwo`
- [ ] `project_charter` artifact written by CWO when not present for approved project
- [ ] Domain strategy dispute routed to CSO (not handled inline by CWO — CWO has `decision: deny`)
- [ ] GATE-005/GATE-006 compliance: CSO review outcome record present in `governance_artifacts` before CEO review

---

## WP M14-04 — Auditor Agent

**Goal:** Implement `AuditorAgent` as the governance compliance monitor. Auditor evaluates audit event streams for policy/budget violations, triggers enforcement actions on breaches, and provides governance findings to owner.

**Design ref:** `spec/governance/roles/AuditorRoleContract.md`, `spec/governance/architecture/EscalationModel.md`

**Entry criteria:** M13 complete (OTel audit writer active from M12, LangGraph wired).

### Tasks

- [ ] Create `src/openqilin/agents/auditor/` package: `agent.py`, `models.py`, `enforcement.py`
- [ ] Implement `AuditorAgent` with oversight authority:
  - Monitor `audit_events` table for policy compliance violations, budget anomalies, and governance rule breaches
  - `evaluate_compliance(audit_event)` — checks event against rule set; flags violations
  - `trigger_enforcement(violation)` — pauses affected task/project; emits immutable enforcement finding record
  - Hard budget breach → immediate escalation to owner (notification via Discord + governance record)
  - Severe governance violations → escalate to owner; notify CEO for operational awareness
- [ ] Implement `enforcement.py` — `AuditorEnforcementService`:
  - `pause_task(task_id, reason, trace_id)` — transitions task to `blocked` via `lifecycle_service`; records enforcement evidence; emits CEO notification (ESC-005: any agent pause MUST notify CEO); if `severity=critical`, also alerts owner immediately (ESC-006)
  - `escalate_to_owner(violation, severity)` — creates owner-bound notification record with `trace_id`, `rule_ids`, and rationale
  - All enforcement actions are immutable (append-only records with `trace_id`)
- [ ] Implement project-document compliance monitoring in `AuditorMonitorLoop`: scan for policy violations on document type/cap/lifecycle/access/integrity (AuditorRoleContract §3); flag violations; escalate to owner
- [ ] Implement behavioral violation handling path: accept behavioral violation escalations routed from PM (EscalationModel: "specialist → PM → auditor → owner"); evaluate and escalate to owner with findings
- [ ] Implement `AuditorMonitorLoop` — periodic or event-driven scan of `audit_events` for new unreviewed violations; runs as background task within LangGraph worker
- [ ] Wire `AuditorAgent` in `dependencies.py`; instantiate with access to `audit_writer`, `lifecycle_service`, and `communication_repo`
- [ ] Add unit tests: hard budget breach → task paused + owner escalation + CEO notified (ESC-005); critical-impact pause → owner immediately alerted (ESC-006); governance rule breach → finding record emitted; enforcement actions are immutable; project-document cap violation → auditor finding escalated to owner; behavioral violation from PM → auditor finding emitted to owner

### Outputs

- `AuditorAgent` active with oversight authority
- Enforcement actions (pause/escalate) wired to lifecycle and communication layers
- Immutable finding records for all enforcement actions

### Done criteria

- [ ] Hard budget breach detected → task paused + owner notified + CEO notified (ESC-005) within one monitor cycle
- [ ] Critical-impact pause → owner alerted immediately, not on next monitor cycle (ESC-006)
- [ ] Enforcement finding records are immutable (append-only; cannot be updated/deleted)
- [ ] Auditor does not issue commands or execute tasks — all actions are oversight-only
- [ ] Escalation to owner includes `trace_id`, `rule_ids`, and rationale
- [ ] Project-document cap violation detected → auditor finding record emitted; owner escalated
- [ ] Behavioral violation routed from PM → auditor evaluates and escalates to owner with immutable finding

---

## WP M14-05 — Administrator Agent

**Goal:** Implement `AdministratorAgent` as the infrastructure and document policy authority. Administrator enforces storage/retention controls, project document caps, and memory lifecycle. Executes containment actions on security incidents.

**Design ref:** `spec/governance/roles/AdministratorRoleContract.md`, `spec/infrastructure/data/StorageAndRetention.md`

**Entry criteria:** M13 complete (PostgreSQL repos active, project artifact model wired).

### Tasks

- [ ] Create `src/openqilin/agents/administrator/` package: `agent.py`, `models.py`, `document_policy.py`, `retention.py`
- [ ] Implement `AdministratorAgent` with oversight authority:
  - **Role boundary: Administrator ENFORCES policy at runtime boundaries (DocumentPolicyEnforcer is the enforcement gate). Auditor MONITORS compliance and escalates findings. Administrator does not scan audit events; Auditor does not enforce write gates. Both emit immutable audit records for their own actions.**
  - Enforce project artifact caps per `ProjectArtifactModel.md §3.1`: per-type cap and total cap (20 per project)
  - `check_artifact_cap(project_id, artifact_type)` — returns `allowed`/`denied`; called before every artifact create
  - `enforce_retention(project_id)` — archives artifacts for completed/terminated projects; marks them read-only
  - Containment actions: `quarantine_agent(agent_id, reason)` — marks agent record `inactive`; notifies owner immediately; notifies CEO for operational awareness; if containment affects runtime availability, escalate to owner immediately (Administrator spec §6)
  - Read infrastructure and storage telemetry to detect retention and integrity anomalies (`StorageAndRetention.md`)
- [ ] Implement `document_policy.py` — `DocumentPolicyEnforcer`:
  - Validates artifact write requests against `ProjectArtifactModel` write contract (role + project state)
  - Blocks writes to prohibited artifact types per role (e.g. PM cannot write `project_charter`)
  - Validates hash integrity: reject write if `content_hash` in DB does not match file-backed content (ProjectArtifactModel §7); emit immutable audit event with denial reason
  - Integrated as a pre-write check in `project_artifact_repo`
- [ ] Implement `retention.py` — `RetentionEnforcer`:
  - `enforce_completed_project(project_id)` — makes all artifacts read-only; archives channel; emits audit record with `STR-001` rule reference
  - `enforce_terminated_project(project_id)` — same as completed; adds termination audit record; references `STR-002`
  - All retention actions emit immutable audit records (rule bindings: `STR-001`, `STR-002`, `STR-005`, `FRM-003`, `FRM-005`)
- [ ] Wire `AdministratorAgent` in `dependencies.py`; wire `DocumentPolicyEnforcer` into artifact repository
- [ ] Add unit tests: artifact cap blocked at limit; PM blocked from writing `project_charter`; containment quarantines agent, notifies owner and CEO; hash mismatch blocks write and emits audit event; retention audit records reference correct rule IDs (STR-001, STR-002)

### Outputs

- `AdministratorAgent` active with oversight authority
- Artifact caps enforced at repository level
- Document policy enforced per `ProjectArtifactModel` write contract
- Retention enforced for completed/terminated projects

### Done criteria

- [ ] Artifact create beyond per-type cap → denied fail-closed
- [ ] PM attempt to write `project_charter` → denied by document policy enforcer
- [ ] Content hash mismatch detected → write denied fail-closed; immutable audit event emitted (ProjectArtifactModel §7)
- [ ] Completed project → all artifact mutations blocked; channel archived; retention audit record references STR-001
- [ ] Agent quarantine → agent record set to `inactive`; owner notified with `trace_id`; CEO notified for operational awareness
- [ ] Containment affecting runtime availability → owner alerted immediately

---

## WP M14-06 — Specialist Agent and Task Execution Engine

**Goal:** Implement `SpecialistAgent` as the task execution worker. Specialists are dispatched only by PM; they cannot be reached directly by owner or other executive agents. Specialists execute assigned tasks, produce artifacts, and escalate blockers to PM.

**Design ref:** `spec/governance/roles/SpecialistRoleContract.md`, `spec/orchestration/control/TaskOrchestrator.md`

**Entry criteria:** WP M14-01 complete (PM dispatch implemented); M13-WP06 complete (sandbox enforcement scaffolding).

### Tasks

- [ ] Create `src/openqilin/agents/specialist/` package: `agent.py`, `models.py`, `prompts.py`, `task_executor.py`
- [ ] Implement `SpecialistRequest` and `SpecialistResponse` in `models.py`:
  - Request: `task_id`, `project_id`, `task_description`, `approved_tools: list[str]`, `trace_id`
  - Response: `execution_status`, `output_text`, `artifact_id: str | None`, `blocker: str | None`, `trace_id`
- [ ] Implement `SpecialistAgent.handle(request)`:
  - Execute assigned task using approved tools only (validated against `approved_tools` list)
  - **SPEC CONFLICT RESOLVED: Specialist has NO direct write path for project artifact types (ProjectArtifactModel §6: "specialist has no direct write path for project documentation types in MVP"). Specialist writes task-level execution results to a `TaskExecutionResult` record (task-scoped, not project-scoped). PM reads these results and synthesizes them into project artifacts (`progress_report`, `execution_plan`).**
  - Write task execution result to `task_execution_results` table: `(task_id, specialist_agent_id, output_text, tools_used, trace_id, created_at)` — task-scoped, not a project artifact
  - Blockers: if task cannot proceed, set `blocker` in response; PM receives blocker for escalation decision
  - Behavioral violations: if task encounters a governance/safety concern, emit behavioral violation event on "specialist → PM" escalation path (EscalationModel §4); PM then routes to auditor if unresolved
  - No direct Discord channel output; all responses routed through PM synthesis
  - Wire Specialist → DL technical clarification path: `request_domain_clarification(question, task_id)` — routes question to DL via PM; receives DL response before continuing task execution (DL interaction path activated in MVP-v2 per M13-WP5)
- [ ] Implement `task_executor.py` — `SpecialistTaskExecutor`:
  - `execute(task_description, approved_tools)` — applies sandbox enforcement (from M13-WP06); runs task; returns execution result
  - Unknown tool → `ToolNotAuthorizedError`; execution denied fail-closed
- [ ] Write Alembic migration for `task_execution_results` table: `(id, task_id, specialist_agent_id, output_text, tools_used, trace_id, created_at)`
- [ ] Enforce PM-dispatch-only: `SpecialistAgent.handle()` rejects requests without a valid `task_id` dispatched by `project_manager` role (validates `dispatch_source_role` in request metadata)
- [ ] Wire `SpecialistAgent` in `dependencies.py` as a dispatch target in `TaskDispatchService` (add `"specialist"` target)
- [ ] Add unit tests: specialist executes task and writes to `task_execution_results` (NOT project artifacts); specialist rejects direct owner request; blocker returned when task cannot proceed; unapproved tool denied; behavioral violation event emitted; DL clarification request routed via PM

### Outputs

- `SpecialistAgent` active as task execution worker
- PM dispatch → specialist execution → artifact write path wired
- PM-dispatch-only enforcement: specialist not directly reachable

### Done criteria

- [ ] PM dispatches task → specialist receives and executes → `TaskExecutionResult` written to `task_execution_results` table (NOT a project artifact — specialist has no direct project artifact write path per ProjectArtifactModel §6)
- [ ] PM reads `TaskExecutionResult` and synthesizes into `progress_report`/`execution_plan` project artifacts
- [ ] Direct request to specialist without PM dispatch → rejected
- [ ] Unapproved tool request → `ToolNotAuthorizedError`; task blocked
- [ ] Behavioral violation event emitted on "specialist → PM" escalation path
- [ ] Specialist → DL clarification request routes via PM synthesis; DL response returned before task continues
- [ ] Specialist blocker → PM receives blocker flag for escalation decision
- [ ] `specialist` added as valid target in `TaskDispatchService`

---

---

## WP M14-07 — File-Backed Artifact Storage

**Goal:** Implement the canonical file-backed storage for project artifacts per `ProjectArtifactModel.md §2.1`. Project-generated files must not be stored in the source repository tree. DB metadata must track `storage_uri`, `content_hash`, and `revision_no` for every artifact version.

**Design ref:** `spec/orchestration/memory/ProjectArtifactModel.md §2.1, §4, §7`

**Entry criteria:** M12 PostgreSQL repos active; WP M14-01 (PM as primary artifact writer) must be underway or complete.

### Tasks

- [ ] Define canonical runtime root: `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/` (default: `${HOME}/.openqilin/projects/<project_id>/`); add `OPENQILIN_SYSTEM_ROOT` to `RuntimeSettings` and `.env.example`
- [ ] Add `storage_uri`, `content_hash` (sha256), and `revision_no` fields to `project_artifact_version` table via Alembic migration
- [ ] Implement `ArtifactFileStore` in `src/openqilin/data_access/artifact_file_store.py`:
  - `write(project_id, artifact_type, version_no, content_md)` → writes file to `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/<artifact_type>-v{version_no}.md`; computes sha256; returns `(storage_uri, content_hash)`
  - `read(storage_uri)` → returns file content as string
  - Files must never be written to the source repository tree
- [ ] Wire `ArtifactFileStore` into `project_artifact_repo` write path: every artifact version write calls `ArtifactFileStore.write()` before DB insert; stores `storage_uri` and `content_hash` in DB record
- [ ] Implement hash integrity check in `DocumentPolicyEnforcer` (WP M14-05): on every artifact write/update, re-compute sha256 of file at `storage_uri`; if mismatch with DB `content_hash`, deny write fail-closed and emit immutable audit event (ProjectArtifactModel §7)
- [ ] Add unit test: artifact write produces file at canonical path + matching DB `storage_uri` and `content_hash`
- [ ] Add unit test: hash mismatch between file and DB `content_hash` → write denied; audit event emitted

### Outputs

- Project artifacts written to canonical file-backed storage root, never to source tree
- `storage_uri` and `content_hash` tracked in DB for every artifact version
- Hash integrity enforcement in `DocumentPolicyEnforcer`

### Done criteria

- [ ] Artifact write produces file at `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/` path
- [ ] `storage_uri` and `content_hash` stored in `project_artifact_version` DB row
- [ ] No project artifact file written under the source repository directory
- [ ] Hash mismatch between DB and file → write denied fail-closed; audit event emitted (ProjectArtifactModel §7)

---

## M14 Exit Criteria

- [ ] All seven WPs above are marked done
- [ ] PM active as default project channel handler; specialist dispatch and DL escalation wired; PM issues status reports/decisions (not advisory text)
- [ ] CEO active with decision authority; project proposal approval flow wired; GATE-003/GATE-004/GATE-005 compliance tested
- [ ] CWO active with workforce authority; DecisionReviewGates full flow wired (CSO → CEO → owner → CWO initialization); reads `completion_report` before co-approval
- [ ] Auditor active; ESC-005/ESC-006 CEO+owner notification on pause wired; immutable finding records produced; project-document and behavioral violation paths handled
- [ ] Administrator active; artifact caps and document policy (including hash integrity) enforced at repository level; STR/FRM rule bindings in audit records
- [ ] Specialist active; PM-dispatch-only enforcement; writes to `task_execution_results`, NOT project artifacts (spec conflict resolved)
- [ ] File-backed artifact storage active; canonical path enforced; `storage_uri` and `content_hash` tracked in DB
- [ ] All agent authority profiles match their spec contracts: no role issues advisory responses outside advisory=allow; no role commands outside command=allow

## References

- `spec/governance/roles/` — all role contracts
- `spec/governance/architecture/DecisionReviewGates.md`
- `spec/orchestration/control/TaskOrchestrator.md`
- `spec/orchestration/memory/ProjectArtifactModel.md`
- `spec/orchestration/registry/AgentRegistry.md`
- `spec/governance/architecture/EscalationModel.md`
- `spec/infrastructure/data/StorageAndRetention.md`
