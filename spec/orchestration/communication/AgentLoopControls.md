# OpenQilin - Agent Loop Controls

Active as of: v2

## 1. Scope
- Defines controls that prevent runaway agent-to-agent conversation loops.
- Covers turn ownership, hop count limits, pair-round limits, cooldown behavior, and terminal actions when caps are hit.
- Applies to all inter-agent communication paths: A2A, ACP, and orchestrator-dispatched workflows.

## 2. Design Principles
- Every agent turn MUST originate from a human prompt or an explicitly governed continuation authorized by the orchestrator.
- Agents MUST NOT autonomously continue bot-to-bot conversation outside a governed orchestration context.
- Loop caps MUST produce a governed terminal action (denial or escalation), not silent continuation or silent failure.

## 3. Turn Ownership Model

```
owner prompt
  → orchestrator admits and governs
    → project_manager (primary project representative)
      → [optional] governed A2A escalation to domain_leader or specialist
        → single answer per hop
          → response returns up the chain
            → single synthesized reply to owner
```

Rules:
- The human prompt starts every governed turn.
- `project_manager` may escalate downstream through governed A2A.
- Downstream agents (`domain_leader`, `specialist`) answer once per governed continuation unless the orchestrator explicitly authorizes a new continuation.
- Institutional roles (`ceo`, `cwo`, `cso`) do not autonomously reply to each other in shared channels; they respond on explicit mention, escalation trigger, or owner prompt.

## 4. Loop Control Limits

The following limits apply per trace (one owner prompt = one trace):

| Control | Limit | Action on Breach |
|---|---|---|
| Maximum inter-agent hop count | 5 hops per trace | Block further dispatch; escalate to owner |
| Maximum rounds per sender/recipient pair | 2 rounds per pair per trace | Block the pair; escalate to PM or owner |
| Cooldown on repeated pair churn | If a pair exceeds its round limit, a cooldown applies before any retry | Deny retry until cooldown clears |
| Hard stop | If both hop count and pair round limits are hit in the same trace | Terminate the trace; generate a governed denial and audit event |

Limit values are provisional defaults. They MUST be configurable per deployment via governed policy without code changes.

## 5. Terminal Actions
When a loop cap is hit, the runtime MUST:
1. Stop further dispatch immediately on the current trace.
2. Emit an audit event recording: trace_id, cap type, sender, recipient, hop count at breach.
3. Either: escalate to the owner (with an explainable summary), or: return a governed denial response.
4. NOT silently retry, continue, or ignore the cap.

## 6. Rule Set
| Rule ID | Statement | Severity | Enforced By |
|---|---|---|---|
| LOOP-001 | Every agent turn MUST originate from a human prompt or an explicitly governed continuation; autonomous bot-to-bot continuation is not permitted. | critical | Task Orchestrator |
| LOOP-002 | Maximum inter-agent hop count per trace MUST be enforced and MUST produce a governed terminal action on breach. | critical | Task Orchestrator |
| LOOP-003 | Repeated sender/recipient pair rounds within one trace MUST be capped and MUST produce a governed terminal action on breach. | critical | Task Orchestrator |
| LOOP-004 | Loop cap breaches MUST emit an audit event before terminating the trace. | high | Observability |
| LOOP-005 | Loop cap limits MUST be configurable via governed policy without requiring code changes. | medium | Policy Engine |

## 7. Conformance Tests
- A trace that exceeds the hop count limit is terminated with a governed denial and an audit event; no further dispatch occurs.
- A sender/recipient pair that exceeds the round limit is blocked; the remaining trace budget is preserved for other pairs.
- An autonomous bot-to-bot reply (not originating from a human prompt or governed continuation) is blocked before dispatch.
- Audit events for loop cap breaches contain: trace_id, cap type, sender, recipient, hop count at breach.
- Loop cap limits are adjustable via policy configuration without code changes.
