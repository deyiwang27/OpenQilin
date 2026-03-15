# OpenQilin - Owner Interaction Grammar

Active as of: v2

## 1. Scope
- Defines the interaction grammar for owner-to-agent communication in MVP-v2.
- Covers intent classification, free-text mode, compact command syntax, and routing-aware interpretation.
- Replaces JSON-shaped daily interaction as the normal operator UX.
- Policy and authority enforcement remain in the constitution and runtime layers. This spec defines only grammar and classification.

## 2. Design Goals
- Normal daily interactions MUST NOT require raw JSON.
- JSON is retained for internal transport, debugging, tests, and advanced admin surfaces only.
- Governed mutations MUST use explicit command syntax or confirmation; they must not be inferred silently from free text.
- The grammar must be portable: defined at the application layer, not tied to Discord-specific slash command primitives.

## 3. Intent Classification

Every owner message is classified into one of four intent classes before routing:

| Intent Class | Description | Canonical Examples |
|---|---|---|
| `discussion` | Open-ended conversation, planning, reasoning, exploration | "What should we prioritize this week?" |
| `query` | Read-only information or status request | "What's the status of Project Alpha?" |
| `mutation` | Explicit governed state change requiring policy authorization | `/oq project pause alpha` |
| `admin` | Operator-level system action | `/oq doctor` |

Intent classification is a runtime routing step, not a UI affordance. Misclassification MUST fail closed: an ambiguous input that cannot be reliably classified MUST not be silently dispatched as a mutation.

## 4. Free-Text Mode

Free text is the default input format for `discussion` and `query` intents:
- No structured syntax required.
- The system infers routing from chat class and project binding context.
- `secretary` is the default triage responder for free-text in institutional shared channels when no recipient is explicitly named.
- `project_manager` is the default responder for free-text in project spaces.
- Free text MUST NOT be silently dispatched as a `mutation`; governed state changes require explicit syntax.

Canonical free-text examples:
- `Give me the latest status of Project Alpha`
- `PM, break this goal into milestones`
- `Auditor, explain the current budget risk`
- `What is blocking the engineering domain right now?`

## 5. Compact Command Syntax

Explicit governed mutations and admin actions use compact command syntax:

```
/oq <verb> [target] [args...]
```

Verb catalog (provisional):

| Category | Verbs |
|---|---|
| Project lifecycle | `project create`, `project approve`, `project pause`, `project resume`, `project close` |
| Routing / ask | `ask <role> [project] <prompt>` |
| Status / read | `status [project]` |
| Governance | `escalate`, `approve`, `deny` |
| Admin / ops | `doctor`, `discord probe`, `governance audit` |

Compact command examples:
- `/oq project create`
- `/oq project pause alpha`
- `/oq ask pm alpha draft milestone plan`
- `/oq status alpha`
- `/oq escalate budget-risk alpha`

A compact command MUST produce a governed envelope that passes through the normal policy and budget gate order, identical to any other governed action.

## 6. Routing-Aware Interpretation

Message interpretation is context-aware. Routing resolves in priority order:

1. Connector and project-space binding (see `ProjectSpaceBindingModel.md`)
2. Chat class
3. Explicit mention or alias target
4. Default recipient for the chat class
5. Governance/policy-triggered escalation
6. Fail-closed denial if ambiguous or unresolvable

## 7. Rule Set
| Rule ID | Statement | Severity | Enforced By |
|---|---|---|---|
| GRAM-001 | Normal owner interactions for `discussion` and `query` intents MUST support free-text input without requiring JSON. | high | Control Plane |
| GRAM-002 | Governed state mutations MUST require explicit compact command syntax or owner confirmation; silent inference from free text is not permitted. | critical | Policy Engine |
| GRAM-003 | Intent classification MUST occur before routing dispatch. | high | Task Orchestrator |
| GRAM-004 | Unresolvable or ambiguous intent MUST fail closed with human-readable and actionable feedback. | critical | Control Plane |
| GRAM-005 | Compact command syntax MUST be defined at the application layer and not depend on Discord-native slash command primitives. | medium | Control Plane |
| GRAM-006 | JSON-shaped input MUST be rejected as a normal owner interaction format; JSON is permitted only for internal transport, debug, test, and advanced admin surfaces. | high | Control Plane |

## 8. Conformance Tests
- Free-text discussion input produces a routed response without requiring JSON.
- Free-text input in a project space routes to `project_manager` without explicit recipient specification.
- Free-text input that could be interpreted as a mutation is not silently dispatched; it is either denied or prompted for explicit confirmation.
- Compact command `/oq project pause alpha` produces a governed mutation envelope that passes through policy and budget gates.
- Unrecognized or ambiguous input produces human-readable feedback and does not dispatch.
- JSON-shaped input in a normal owner interaction context is rejected with an explainable error.
