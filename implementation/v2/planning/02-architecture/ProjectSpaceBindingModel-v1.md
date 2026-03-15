# Project Space Binding Model

Date: `2026-03-14`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Define the runtime binding model that connects Discord spaces to OpenQilin project execution.
- Replace v1-style project-bot identity assumptions with an explicit conversation and project-space binding layer.
- Make routing, persistence, and recovery behavior concrete enough for implementation planning.

## 2. Problem Statement

MVP-v1 binds too much routing behavior to Discord bot identity and manual channel assumptions.

MVP-v2 needs a stable way to answer:
- what project does this message belong to
- what kind of chat surface is this
- who should respond by default
- which roles are allowed to be invoked here
- what should happen after restart or Discord-side changes

That requires a first-class project-space binding model.

## 3. Design Goal

Introduce a runtime-owned binding object that maps an external chat surface to governed OpenQilin context.

The binding layer should separate:
- transport identity
- conversation surface
- project context
- routing defaults
- authority constraints

## 4. Core Principles

### 4.1 Bind spaces, not personalities
- Discord channels and threads should bind to project context.
- PM and DL should be virtual runtime roles, not standalone Discord identities.

### 4.2 Make routing deterministic
- Default routing should come from binding metadata, not fragile heuristics.

### 4.3 Keep bindings persistent
- Bindings should survive restart and be recoverable.
- Project execution should not depend on transient in-memory channel assumptions.

### 4.4 Fail closed on ambiguity
- Missing or conflicting bindings should deny or request repair, not silently guess.

### 4.5 Keep project lifecycle visible in binding state
- Lifecycle changes should affect what the bound space permits and how it routes.

## 5. Proposed Runtime Object

### 5.1 `project_space_binding`

Suggested fields:
- `binding_id`
- `connector`
- `guild_id`
- `channel_id`
- `thread_id`
- `external_space_type`
- `chat_class`
- `project_id`
- `default_recipient_role`
- `default_recipient_id`
- `allowed_recipient_roles`
- `status`
- `created_at`
- `updated_at`
- `last_validated_at`
- `lifecycle_mode`
- `metadata`

Notes:
- `thread_id` is optional when the binding is channel-level.
- `default_recipient_id` may be something like `project_manager::<project_id>`.
- `status` should distinguish active, archived, revoked, and invalid bindings.

## 6. Recommended Binding Types

### 6.1 Institutional shared-space binding
- used for `leadership_council`, `executive`, `governance`
- usually `project_id = null`
- routing driven by mentions, prompts, and policy escalation

### 6.2 Project-space binding
- one binding per project channel or project thread
- `project_id` required
- default recipient is PM
- lifecycle-aware restrictions apply

### 6.3 Direct institutional DM binding
- used for owner-to-institutional-role DM surfaces
- project context optional or absent
- not valid for PM/DL surfaces

## 7. Routing Resolution Order

Recommended resolution:

1. locate binding by connector and external IDs
2. validate binding status
3. determine chat class and project context
4. apply lifecycle restrictions
5. resolve explicit mention or alias target if present
6. otherwise use default recipient from binding
7. apply governance and policy checks
8. fail closed if unresolved or forbidden

## 8. Lifecycle Behavior

### 8.1 Proposed project
- binding exists
- PM may exist logically but project participation rules are more restricted
- project space may be visible but not yet fully active

### 8.2 Active project
- PM is default recipient
- normal project communication allowed
- dashboard and alert links available

### 8.3 Paused project
- project remains inspectable
- active execution routing may be restricted
- PM can explain paused status and resume path

### 8.4 Completed or terminated project
- bound space becomes read-mostly
- query and closeout behavior remains allowed
- mutation routing is restricted fail-closed

### 8.5 Archived project
- binding remains as historical reference or is marked archived
- new operational routing is blocked

## 9. Automation Responsibilities

When Discord remains the primary surface, the binding layer should support:
- automatic project space creation
- initial binding registration
- rename and move operations
- archive and lock operations
- validation after restart
- repair workflows when Discord-side state drifts

## 10. Recovery and Drift Handling

The runtime should detect and handle:
- missing bound channel or thread
- archived/deleted external space
- project mismatch
- revoked or invalid identity/channel mapping
- inconsistent lifecycle state

Suggested responses:
- mark binding invalid
- surface alert to Secretary or owner
- fail closed for writes
- allow limited read-only diagnostics where safe

## 11. Relationship to the Dashboard

The binding object should also support:
- project detail deep links
- dashboard-to-Discord navigation
- validation of which project a dashboard view belongs to

This helps keep Discord and dashboard surfaces aligned to the same project identity.

## 12. MVP-v2 Scope Recommendation

For MVP-v2, keep the model narrow:
- Discord only
- one project binding per project space
- PM as the only default virtual recipient
- explicit mention routing only for institutional roles
- DL and specialist behind PM

Avoid for MVP-v2:
- multi-adapter binding complexity
- many nested binding types
- exposed project-scoped virtual mention semantics beyond PM aliases if not needed

## 13. Open Design Questions

- channel per project or thread per project as the primary unit
- whether project proposal spaces should reuse final project spaces
- whether dashboard actions can open or validate bindings directly
- whether alias invocation like `@pm` should be implemented in MVP-v2 or deferred
