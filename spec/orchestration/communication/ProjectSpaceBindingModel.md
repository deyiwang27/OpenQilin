# OpenQilin - Project Space Binding Model

Active as of: v2

## 1. Scope
- Defines how runtime-managed Discord channels or threads are bound to governed project contexts.
- Covers binding persistence, lifecycle automation, routing defaults, and recovery behavior.
- Does not define channel membership policy (see `OwnerInteractionModel.md`), interaction grammar (see `OwnerInteractionGrammar.md`), or loop controls (see `AgentLoopControls.md`).

## 2. Design Principles
- Project spaces are the primary communication surface for project execution.
- Binding is runtime-owned: the system creates, manages, and retires project spaces automatically; operators do not configure per-project Discord channels manually.
- Channel or thread identity is transport metadata. Governed project context (`project_id`, lifecycle state, default routing) is authoritative in the runtime data store, not in Discord.
- Project-scoped workforce roles (`project_manager`, `domain_leader`) are backend-routed virtual agents. They are not standalone Discord bot identities.

## 3. Binding Model

### 3.1 Project Space Definition
A project space is a single Discord channel or thread bound to one project:
- One project space per approved or active project (one-to-one)
- Created automatically by the runtime after project approval and before the first active interaction
- No manual operator action is required beyond the initial Discord app install and permission grant

### 3.2 Binding Record
Each binding is a persisted PostgreSQL record containing:
- `project_id` — authoritative governed project identifier
- `guild_id` — Discord server identifier
- `channel_id` or `thread_id` — Discord surface identifier
- `binding_state` — one of: `pending`, `active`, `read_only`, `locked`
- `default_recipient` — always `project_manager` for active project spaces
- `project_lifecycle_state` — snapshot of project state for routing and automation
- `created_at`, `updated_at`

### 3.3 Routing Default
- All inbound messages in a project space route to `project_manager` by default.
- Executive roles (`ceo`, `cwo`, `cso`) respond only on explicit mention or policy-triggered escalation.
- `domain_leader` is not a default participant in project spaces; it is surfaced only through PM escalation or governed review paths.
- Ambiguous routing in the absence of a valid binding fails closed.

### 3.4 Lifecycle Automation
Project space binding state transitions with project lifecycle:

| Project State | Binding State | Behavior |
|---|---|---|
| `proposed` | `pending` | Space not yet created |
| `approved` | `active` | Space created; PM-default routing active |
| `active` | `active` | Normal operation |
| `paused` | `active` | PM available; reduced activity expected |
| `completed` | `read_only` | No new messages; governed closeout flows only |
| `terminated` | `read_only` | No new messages; governed closeout flows only |
| `archived` | `locked` | No messages; channel/thread archived by runtime |

### 3.5 Persistence and Recovery
- Binding records MUST be persisted in PostgreSQL; in-memory-only binding is not sufficient.
- On startup, the runtime MUST reload active bindings from PostgreSQL before accepting inbound messages.
- A missing binding for an inbound project-space message MUST fail closed with a governed denial and an emitted audit event.

## 4. Rule Set
| Rule ID | Statement | Severity | Enforced By |
|---|---|---|---|
| PSB-001 | Every approved or active project MUST have exactly one bound project space. | critical | Task Orchestrator |
| PSB-002 | Project space creation and lifecycle transitions MUST be performed automatically by the runtime after initial Discord app install. | high | Discord Adapter |
| PSB-003 | All inbound messages in a project space MUST default to `project_manager` as the routing recipient. | critical | Task Orchestrator |
| PSB-004 | Project space binding records MUST be persisted in PostgreSQL; in-memory-only binding is not acceptable. | critical | Data Access |
| PSB-005 | Project spaces MUST transition to read-only or locked on terminal project lifecycle states, except for governed closeout flows. | high | Task Orchestrator |
| PSB-006 | A missing or unresolvable binding for an inbound project-space message MUST fail closed with a governed denial. | critical | Policy Engine |
| PSB-007 | Binding state MUST be recovered from PostgreSQL on startup before inbound project-space messages are processed. | critical | Control Plane |

## 5. Conformance Tests
- An approved project produces a bound project space before its first active interaction.
- Binding records survive process restart and are reloaded correctly from PostgreSQL.
- An inbound message with no matching binding is denied with a governed denial and an audit event.
- Messages in an active project space route to `project_manager` without explicit recipient specification.
- Project space transitions to read-only when the project reaches `completed` or `terminated`.
- Project space is locked when the project reaches `archived`.
- `domain_leader` does not appear as a default participant in a project space channel.
