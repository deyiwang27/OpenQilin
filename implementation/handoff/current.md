# Handoff: M14-WP4 — Auditor Agent

**WP:** M14-WP4
**GitHub issue:** #108
**Milestone tracker:** #100
**Branch to create:** `feat/m14-wp4-auditor-agent`
**Base:** `main`
**Date:** 2026-03-18

---

## Context

M14-WP1–WP3 are complete. `ProjectManagerAgent`, `CeoAgent`, and `CwoAgent` are all wired into `RuntimeServices`. M14-WP4 implements `AuditorAgent` as the governance compliance monitor — the role that scans audit events, triggers enforcement actions on breaches, and escalates findings to owner. Auditor has `oversight: allow` and all other authority values `deny`. It must never issue commands or execute tasks.

Key existing interfaces to call:
- `OTelAuditWriter.write_event(...)` — for writing immutable enforcement finding records to PostgreSQL + OTel
- `TaskLifecycleService.mark_blocked_dispatch(task_id, ...)` — for pausing a task (transition to `blocked`)
- `PostgresGovernanceArtifactRepository.write_project_artifact()` — for writing escalation evidence records
- `PostgresAuditEventRepository` — for reading `audit_events` rows to scan for violations
- `LocalDeliveryPublisher.publish(PublishRequest(...))` — for owner/CEO Discord notifications (communication_repo uses this)

---

## Spec References (read before coding)

- `spec/governance/roles/AuditorRoleContract.md` — authority profile, data access, escalation, ESC-008
- `spec/governance/architecture/EscalationModel.md` — ESC-001 through ESC-008, trigger catalog, event contract
- `implementation/v2/planning/05-milestones/M14-WorkPackages-v1.md` — WP M14-04 task list and done criteria

---

## Files to Create

### `src/openqilin/agents/auditor/__init__.py`
Empty init exposing `AuditorAgent`, `AuditorRequest`, `AuditorResponse`.

### `src/openqilin/agents/auditor/models.py`

```python
@dataclass(frozen=True, slots=True)
class AuditorRequest:
    event_type: str           # "budget_breach" | "governance_violation" | "behavioral_violation" | "document_violation" | "query"
    task_id: str | None       # task affected (required for pause actions)
    project_id: str | None    # project scope
    severity: str             # "low" | "medium" | "high" | "critical"
    rule_ids: tuple[str, ...]  # violated rule IDs (e.g. ("BUD-001", "ESC-003"))
    rationale: str            # description of the violation
    source_agent_role: str | None  # "project_manager" | "specialist" | etc. (for ESC-008 bypass check)
    trace_id: str

@dataclass(frozen=True, slots=True)
class AuditorResponse:
    action_taken: str | None  # "task_paused" | "owner_escalated" | "ceo_notified" | "finding_recorded" | "no_action"
    finding_id: str | None    # governance artifact ID of the immutable finding record
    advisory_text: str        # oversight summary (AuditorAgent has advisory:deny — frame as findings/oversight, not advice)
    trace_id: str

class AuditorFindingError(RuntimeError):
    """Raised when a finding record cannot be written (enforcement path failure)."""
```

### `src/openqilin/agents/auditor/enforcement.py`

```python
class AuditorEnforcementService:
    """Executes enforcement actions on governance violations.

    All actions are append-only (immutable). Never updates or deletes records.
    """

    def __init__(
        self,
        lifecycle_service: TaskLifecycleService,
        governance_repo: PostgresGovernanceArtifactRepository,
        audit_writer: OTelAuditWriter,
        communication_repo: PostgresCommunicationRepository,
    ) -> None: ...

    def pause_task(
        self,
        task_id: str,
        *,
        reason: str,
        severity: str,
        rule_ids: tuple[str, ...],
        trace_id: str,
    ) -> str:
        """Transition task to blocked; write enforcement finding; notify CEO (ESC-005).

        If severity == "critical": also alert owner immediately (ESC-006).

        Returns the finding_id of the written enforcement record.

        Steps:
        1. Call lifecycle_service.mark_blocked_dispatch(task_id, error_code="auditor_enforcement",
              message=reason, dispatch_target="auditor", outcome_source="auditor_enforcement")
           — this transitions task to blocked state.
        2. Write immutable enforcement finding record via audit_writer.write_event(
              event_type="auditor_enforcement", outcome="blocked", task_id=task_id,
              source="auditor", reason_code="auditor_pause", trace_id=trace_id,
              rule_ids=rule_ids, policy_version="v2", policy_hash="auditor-v1",
              message=reason, ...)
        3. Write CEO notification record via governance_repo.write_project_artifact(
              artifact_type="auditor_ceo_notification", author_role="auditor",
              project_id=project_id, trace_id=trace_id) (ESC-005)
        4. If severity == "critical":
              Write owner alert record via governance_repo.write_project_artifact(
              artifact_type="auditor_owner_alert", author_role="auditor",
              project_id=project_id, trace_id=trace_id) (ESC-006)
        """

    def escalate_to_owner(
        self,
        *,
        project_id: str | None,
        rule_ids: tuple[str, ...],
        rationale: str,
        severity: str,
        trace_id: str,
    ) -> str:
        """Create owner-bound escalation record.

        Writes governance artifact with artifact_type="auditor_owner_escalation",
        author_role="auditor", trace_id, and content including rule_ids + rationale.

        Returns the finding_id.
        """

    def record_finding(
        self,
        *,
        project_id: str | None,
        finding_type: str,
        rule_ids: tuple[str, ...],
        rationale: str,
        trace_id: str,
    ) -> str:
        """Write an immutable compliance finding record.

        artifact_type="auditor_finding", author_role="auditor".
        Returns the finding_id.
        """
```

### `src/openqilin/agents/auditor/agent.py`

```python
class AuditorAgent:
    def __init__(
        self,
        enforcement: AuditorEnforcementService,
        governance_repo: PostgresGovernanceArtifactRepository,
        audit_writer: OTelAuditWriter,
        trace_id_factory: Callable[[], str] | None = None,
    ) -> None: ...

    def handle(self, request: AuditorRequest) -> AuditorResponse:
        # Route by event_type:
        #   "budget_breach"          → _handle_budget_breach()
        #   "governance_violation"   → _handle_governance_violation()
        #   "behavioral_violation"   → _handle_behavioral_violation()
        #   "document_violation"     → _handle_document_violation()
        #   "query"                  → _handle_query()
        #   unknown                  → record finding, return "finding_recorded" (fail-closed)

    def _handle_budget_breach(self, request: AuditorRequest) -> AuditorResponse:
        # Hard budget breach path (ESC-003):
        # 1. If task_id present: pause_task via enforcement.pause_task()
        #    (ESC-005: CEO notification written inside pause_task)
        #    (ESC-006: if severity==critical, owner alert also written inside pause_task)
        # 2. Escalate to owner via enforcement.escalate_to_owner() with rule_ids + rationale
        # 3. Return AuditorResponse(action_taken="task_paused", finding_id=...)
        #    If no task_id: just escalate_to_owner + record_finding; action_taken="owner_escalated"

    def _handle_governance_violation(self, request: AuditorRequest) -> AuditorResponse:
        # Governance rule breach:
        # 1. Write immutable finding record via enforcement.record_finding()
        # 2. Escalate to owner via enforcement.escalate_to_owner()
        # 3. If severity in ("high", "critical"): also write CEO notification (awareness)
        # 4. Return action_taken="owner_escalated"

    def _handle_behavioral_violation(self, request: AuditorRequest) -> AuditorResponse:
        # Behavioral violation path (ESC-008 PM bypass applies):
        # source_agent_role is the violating agent
        # 1. Write immutable finding record
        # 2. Escalate directly to owner (bypasses the violating agent's chain — AuditorRoleContract §6)
        # 3. Notify CEO for operational awareness
        # 4. Return action_taken="owner_escalated"
        # Note: Auditor may NOT re-escalate for the same task+agent without new evidence.
        #       Check governance_repo for existing auditor_finding with same project_id+task_id
        #       before writing. If already present: return action_taken="no_action" with rationale.

    def _handle_document_violation(self, request: AuditorRequest) -> AuditorResponse:
        # Project-document policy violation (cap/type/lifecycle/access/integrity):
        # 1. Write immutable finding record via enforcement.record_finding()
        # 2. Escalate to owner via enforcement.escalate_to_owner()
        # 3. Return action_taken="owner_escalated"

    def _handle_query(self, request: AuditorRequest) -> AuditorResponse:
        # Status/compliance query — return oversight summary
        # No writes. Return action_taken="no_action", advisory_text=oversight summary

    def _finding_already_exists(self, project_id: str | None, task_id: str | None) -> bool:
        # Check governance_repo for existing "auditor_finding" artifact for project_id
        # If task_id provided: check payload for task_id match
        # Returns True if duplicate finding would be issued for same task+agent
```

---

## Files to Modify

### `src/openqilin/control_plane/api/dependencies.py`

1. Import `AuditorAgent`, `AuditorEnforcementService`.
2. Add `auditor_agent: AuditorAgent` to `RuntimeServices` dataclass.
3. In `build_runtime_services()`:
   ```python
   auditor_enforcement = AuditorEnforcementService(
       lifecycle_service=lifecycle_service,
       governance_repo=governance_repo,
       audit_writer=audit_writer,
       communication_repo=communication_repo,
   )
   auditor_agent = AuditorAgent(
       enforcement=auditor_enforcement,
       governance_repo=governance_repo,
       audit_writer=audit_writer,
   )
   ```
4. Add `auditor_agent` to `RuntimeServices(...)` construction call.
5. Add `get_auditor_agent(request)` provider function.

### `tests/component/conftest.py`
Add `AuditorAgent` + `AuditorEnforcementService` construction using stub lifecycle/governance/audit_writer stubs (mirroring the pattern used for CwoAgent in this file).

---

## Tests to Write

File: `tests/unit/test_m14_wp4_auditor_agent.py`

```
class TestAuditorBudgetBreach:
    test_budget_breach_pauses_task_when_task_id_present
    test_budget_breach_writes_ceo_notification  # ESC-005
    test_budget_breach_critical_writes_owner_alert  # ESC-006
    test_budget_breach_escalates_to_owner
    test_budget_breach_without_task_id_escalates_owner_only

class TestAuditorGovernanceViolation:
    test_governance_violation_writes_immutable_finding
    test_governance_violation_escalates_to_owner
    test_governance_high_severity_notifies_ceo

class TestAuditorBehavioralViolation:
    test_behavioral_violation_escalates_directly_to_owner  # ESC-008 bypass
    test_behavioral_violation_notifies_ceo
    test_behavioral_violation_pm_bypass_does_not_route_through_pm  # ESC-008
    test_behavioral_violation_duplicate_suppressed_without_new_evidence
    test_behavioral_violation_writes_immutable_finding

class TestAuditorDocumentViolation:
    test_document_cap_violation_writes_finding
    test_document_cap_violation_escalates_to_owner

class TestAuditorAuthorityProfile:
    test_auditor_cannot_issue_commands         # no action_taken=="task_executed"
    test_auditor_cannot_approve_or_deny        # no decision framing
    test_auditor_query_returns_no_action

class TestAuditorEnforcementService:
    test_pause_task_transitions_to_blocked
    test_pause_task_writes_enforcement_finding
    test_pause_task_critical_writes_owner_alert   # ESC-006
    test_escalate_to_owner_includes_trace_rule_rationale
    test_record_finding_is_append_only
```

---

## Key Constraints — Must Not Get Wrong

1. **`oversight: allow` only — all other authority: `deny`** — AuditorAgent must never write in `advisory_text` that it "approves", "decides", "commands", or "advises" anything. Findings and oversight summaries only. No decision framing, no commands.

2. **ESC-005: every pause must notify CEO** — `pause_task()` must always write the CEO notification record regardless of severity. This is mandatory, not conditional.

3. **ESC-006: critical-impact pause → owner alert is immediate** — write the owner alert record in the same call as the pause, before returning. Do not defer or background it.

4. **ESC-008: PM violation bypass** — `_handle_behavioral_violation()` must escalate directly to owner without routing through PM. The violating agent role is in `request.source_agent_role`; there is no special handling per agent type — the bypass applies for all `behavioral_violation` events.

5. **Duplicate suppression (AuditorRoleContract §6)** — Auditor may not reissue the same finding for the same task/agent without new evidence. Check `governance_repo` for an existing `auditor_finding` artifact before writing. If found: return `action_taken="no_action"`, do not write a duplicate record.

6. **Immutable records — no update/delete** — All enforcement finds, escalations, and notifications are written via `write_project_artifact()`. Never call any update or delete operation on these records.

7. **Fail-closed on unknown event_type** — unknown event types must result in a finding record being written and `action_taken="finding_recorded"`, never silently discarded.

---

## Patterns to Follow

- Constructor pattern: `__init__(self, enforcement, governance_repo, audit_writer, trace_id_factory=None)` — see `CeoAgent`.
- Governance record writes: use `PostgresGovernanceArtifactRepository.write_project_artifact()` with `artifact_type="auditor_finding"` / `"auditor_enforcement"` / `"auditor_owner_escalation"` / `"auditor_ceo_notification"` / `"auditor_owner_alert"`.
- Policy audit metadata: `policy_version="v2"`, `policy_hash="auditor-v1"`, `rule_ids=("AUD-001", "ESC-001", "ESC-002")` (vary rule_ids per event type).
- `audit_writer.write_event(...)` for immutable OTel+PostgreSQL audit trail entries (AUD-001 semantics).
- Error classes: `RuntimeError` subclass — see `AuditorFindingError`.
- Lifecycle pause: `lifecycle_service.mark_blocked_dispatch(task_id, error_code="auditor_enforcement", message=reason, dispatch_target="auditor", outcome_source="auditor_enforcement")`.

---

## Done Criteria Checklist (close issue #108 when all pass)

- [ ] Hard budget breach → task paused + owner notified + CEO notified (ESC-005)
- [ ] Critical-impact pause → owner alerted immediately (ESC-006)
- [ ] Enforcement finding records are immutable (append-only; no update/delete)
- [ ] Auditor does not issue commands or execute tasks (oversight-only)
- [ ] Escalation to owner includes `trace_id`, `rule_ids`, and rationale
- [ ] Project-document cap violation → auditor finding record + owner escalated
- [ ] Behavioral violation from PM → auditor evaluates + immutable finding + owner escalation (ESC-008 bypass)
- [ ] Duplicate finding suppressed without new evidence (AuditorRoleContract §6)
- [ ] `AuditorAgent` wired in `RuntimeServices`
- [ ] All unit tests pass; `uv run pytest -m no_infra tests/unit/` clean; ruff + mypy 0 errors

---

## On Completion

When done, create a draft PR targeting `main`, write `implementation/handoff/HANDOFF_COMPLETE.md` with:
- Branch name and PR URL
- Test results (`uv run pytest -m no_infra tests/unit/` output summary)
- Any REVIEW_NOTEs
- Confirm: `grep -r --include="*.py" -l "class InMemory" src/ | grep -v "/testing/"` returns empty
