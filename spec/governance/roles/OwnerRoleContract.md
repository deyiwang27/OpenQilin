# OpenQilin - Owner Role Contract Specification

## 1. Scope
- Defines the formal contract for the `owner` principal (human operator).
- Establishes authority bounds, interaction constraints, and accountability obligations.
- Even as the ultimate authority, the owner operates within formal constraints documented here.

## 2. Role Identity
- `role_id`: `owner`
- `display_name`: `Owner`
- `role_layer`: `principal`
- `reports_to`: — (no agent superior; owner is the human authority)
- `informs`: all agents

## 3. Primary Duties
- Set strategic direction, project goals, and constitutional policy.
- Approve project proposals, completion reports, and governance escalations.
- Issue emergency commands when governance or safety requires direct intervention.
- Review and act on alerts, escalations, and audit findings surfaced by governance agents.

## 4. Authority Profile
| Authority | Value |
| --- | --- |
| decision | allow |
| command | allow |
| execution | deny |
| review | allow |
| advisory | allow |
| oversight | allow |
| workforce | allow |

`execution: deny` — owner does not directly execute tasks; execution routes through operational agents.

## 5. Interaction Channels
- All channel classes defined in `OwnerInteractionModel §2.1` are available to owner.
- Owner may direct-message: `administrator`, `auditor`, `ceo`, `cwo`, `cso`, `secretary`.
- Owner may NOT direct-message: `project_manager`, `domain_leader`, `specialist` (routes through executive layer).

## 6. Formal Constraints

Owner authority is not unbounded. The following constraints apply:

- **No agent impersonation:** Owner cannot issue commands that claim to originate from another agent role.
- **No retroactive audit mutation:** Owner cannot alter, delete, or suppress `audit_events` records after they are written. Audit records are immutable once committed.
- **No completion_report bypass:** Owner cannot seal a `completion_report` that has not been reviewed; the sealing event is the owner approval record, not a bypass of the gate flow.
- **No direct specialist command:** Owner cannot directly command `specialist` agents. Specialist interactions route through `project_manager` (OIM-005).
- **Gate flow participation:** Owner participates in GATE-004 (final approval) only. Owner does not bypass earlier gate stages (CSO review, CEO+CWO review) unilaterally, except via explicit `gate_override` command with mandatory justification.
- **Auditor override accountability:** When owner issues `auditor_override` to clear a behavioral flag, the override must be recorded in `audit_events` with `overridden_by: owner` and a mandatory justification field.

## 7. Emergency Authority
- Owner override is the ultimate authority for safety containment.
- Emergency commands bypass normal gate flows but must still emit immutable audit records (SAF-004, AUD-001).
- Owner may authorize exceptions to AUTH-003 (system-level workforce actions by non-CWO) through an explicit constitutional override workflow.

## 8. Normative Rule Bindings
- `SAF-004`: owner override capability MUST remain available and auditable.
- `OIM-001`, `OIM-002`, `OIM-003`, `OIM-005`
- `AUTH-001`, `AUTH-002`, `AUTH-003`
- `AUD-001`
- `GATE-004`

## 9. Conformance Tests
- Owner commands that impersonate another agent role are rejected.
- Owner attempt to mutate or delete existing audit_events records is denied.
- Owner direct command to specialist is blocked; routes through project_manager.
- gate_override commands include mandatory justification field; omission is denied.
- Emergency owner override commands emit immutable audit records.
