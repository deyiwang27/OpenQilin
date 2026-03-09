# OpenQilin - RFC 01: Orchestration, Governance, and Control Plane

## 1. Scope
Domains in this RFC:
- Orchestration framework: LangGraph vs multi-framework strategy (AutoGen, CrewAI)
- External swarm runtime option: Kimi K2.5 AgentSwarm
- Agent communication: A2A and ACP positioning
- Policy runtime: Open Policy Agent (OPA)
- Control plane/API split: FastAPI + FastMCP
- Tool management model: MCP vs Skills

Timebox:
- Spike (documentation and architecture decision only)
- Date: 2026-03-09

## 2. Investigation Questions
- Is LangGraph sufficient as the default orchestrator, or should OpenQilin include AutoGen/CrewAI in v1 core?
- Is Kimi K2.5 AgentSwarm cost-efficient enough for core dependency, or better as optional burst capacity?
- What are A2A and ACP, and are they the best communication options for OpenQilin?
- What is OPA, and how should it be applied in this project?
- Should tool management be MCP-based, Skills-based, or hybrid?

## 3. Candidate Evaluation Matrix
| Domain | Candidate | Decision | Confidence | Conformance Impact | Notes |
| --- | --- | --- | --- | --- | --- |
| orchestration core | LangGraph | adopt (v1 default) | high | positive | Durable execution + interrupts + memory support fit governance gates. |
| orchestration alt | AutoGen | defer (adapter only) | medium | neutral | Strong multi-agent framework, but adds cognitive/operational surface too early. |
| orchestration alt | CrewAI | defer (adapter only) | medium | neutral | Good crew/flow abstraction; same early-stage complexity concern. |
| external parallel runtime | Kimi K2.5 AgentSwarm | adopt as optional burst executor, not core dependency | medium-low | neutral | Potential cost upside, but published enterprise-grade operational details are limited. |
| agent communication | A2A | adopt as baseline inter-agent protocol | medium-high | positive | Open interoperability direction; complements MCP. |
| agent communication | ACP | defer as independent protocol; keep as internal reliability profile on top of A2A if needed | medium | positive | “ACP” naming is ambiguous in ecosystem; avoid protocol confusion in v1. |
| policy runtime | OPA | adopt as authoritative policy decision point (fail-closed) | high | strong positive | Mature policy engine with decoupled policy/data model and bundle distribution model. |
| control plane API | FastAPI | adopt | high | positive | Pragmatic Python control-plane fit. |
| MCP bridge | FastMCP | adopt as tool-exposure boundary (non-authoritative for policy) | medium-high | positive | Keep governance checks in orchestrator + OPA path. |
| tool model | MCP + Skills hybrid | adopt | high | strong positive | MCP standardizes invocation; Skills standardize governed capability packaging. |

## 4. Spike Findings and Decisions

### 4.1 LangGraph vs AutoGen/CrewAI
Decision:
- Use LangGraph as canonical orchestration runtime for v1.
- Keep AutoGen and CrewAI out of core; evaluate later behind adapter boundary.

Rationale:
- LangGraph explicitly targets long-running, stateful agent workflows with durable execution, interrupts, and memory capabilities, which align with OpenQilin governance gates and pause/resume requirements.
- Multi-framework core at this stage increases implementation variance, testing matrix size, and policy-conformance risk.

Pros of LangGraph-only core now:
- Deterministic orchestration boundary for policy checks and audit.
- Smaller conformance surface.
- Faster path to architecture baseline.

Cons:
- Potential lock-in to one orchestration model in early versions.
- Need adapter strategy if future frameworks are adopted.

### 4.2 Kimi K2.5 AgentSwarm Cost-Efficiency
Decision:
- Do not make AgentSwarm a mandatory core runtime dependency in v1.
- Use it as an optional burst/external parallel execution provider behind strict budget/policy gates.

Rationale:
- Official Moonshot materials indicate strong cost optimization direction (including context caching and pricing adjustments), but spike data is insufficient to guarantee stable cost/SLA outcomes across OpenQilin workloads.
- Cost-efficiency is highly workload-dependent (prompt reuse ratio, context length, failure retry rates, routing policy).

Policy for v1:
- Default internal orchestrator path remains primary.
- External AgentSwarm invocation requires:
  - budget pre-check
  - explicit task eligibility policy
  - full audit event emission
  - deterministic fallback path on failure/timeout

### 4.3 A2A and ACP for Agent Communication
Definitions:
- A2A: an open agent-to-agent interoperability protocol focused on cross-agent communication and collaboration.
- ACP: currently ambiguous term in ecosystem (used by different initiatives/protocols).

Decision:
- Adopt A2A as baseline protocol direction for inter-agent communication.
- Defer ACP as a standalone protocol commitment in v1.
- If reliability extensions are required, define an OpenQilin communication profile layered on A2A (acks/retry/dead-letter/idempotency), without claiming external ACP compatibility unless explicitly validated.

Pros of A2A baseline:
- Open interoperability momentum.
- Explicit positioning as complementary to MCP, which aligns with tool-interop strategy.

Cons:
- Spec/tooling maturity still evolving.
- May require project-specific reliability profile for production guarantees.

### 4.4 OPA in OpenQilin
Definition:
- OPA is a general-purpose policy engine that externalizes policy decisions from application logic.

Decision:
- Adopt OPA as authoritative policy decision component in governance-critical flows.

Application pattern for OpenQilin:
- Orchestrator sends policy input context to OPA before sensitive actions.
- OPA returns allow/deny/obligation outputs.
- Fail-closed behavior for policy evaluation failures on protected operations.
- Use policy bundle distribution/versioning for controlled policy rollout.

Benefits:
- Clear policy/code separation.
- Better auditability and change control.
- Consistent enforcement across orchestration and tool invocation paths.

### 4.5 MCP vs Skills for Tool Management
Decision:
- Adopt hybrid model.

Model:
- MCP for runtime tool transport/discovery/invocation interoperability.
- Skills for governed capability packaging (intent, constraints, policy tags, usage boundaries).

Pros:
- Keeps tool connectivity standard and portable.
- Keeps agent behavior/capability governance explicit and reviewable.

Cons:
- Requires additional lifecycle management for skill definitions.
- Needs strict mapping from skill -> allowed MCP tools.

## 5. Recommended v1 Architecture Boundary
Control plane:
- FastAPI as primary API/service boundary.
- OPA as policy decision point.
- LangGraph as canonical orchestration runtime.

Tool plane:
- FastMCP/MCP server boundary for external/internal tools.
- Skills registry as governance wrapper over raw MCP tools.

Communication plane:
- A2A envelope baseline.
- OpenQilin reliability profile on top of A2A for ack/retry/idempotency/dead-letter.

External execution:
- Optional AgentSwarm provider via adapter interface only.
- Treated as non-authoritative and replaceable.

## 6. Risks and Mitigations
- Risk: ecosystem protocol churn (A2A/ACP naming and scope).
- Mitigation: pin OpenQilin profile version and document compatibility claims explicitly.

- Risk: policy bypass through direct tool invocation.
- Mitigation: enforce policy check at orchestrator and gateway, fail-closed for protected actions.

- Risk: external runtime cost drift.
- Mitigation: per-task budget gate, provider quotas, route-to-internal fallback.

- Risk: over-complexity from multi-framework orchestration.
- Mitigation: single core orchestrator in v1; adapters only after conformance stability.

## 7. Implementation Sequence Recommendation
1. Lock LangGraph + OPA + FastAPI core contracts.
2. Finalize A2A envelope and OpenQilin reliability profile.
3. Add MCP tool bridge and skill-to-tool governance mapping.
4. Introduce AgentSwarm adapter as optional provider after baseline conformance checks.

## 8. Adopt/Defer Summary
Adopt now:
- LangGraph (core orchestration)
- OPA (authoritative policy runtime)
- FastAPI (control plane API)
- MCP/FastMCP + Skills hybrid (tool management)
- A2A (baseline inter-agent protocol)

Defer or scope-limit:
- AutoGen and CrewAI as core runtime components
- ACP as independent committed protocol in v1
- AgentSwarm as mandatory dependency

## 9. Sources (Primary)
- LangGraph Overview: https://docs.langchain.com/oss/python/langgraph/overview
- Microsoft AutoGen repository: https://github.com/microsoft/autogen
- CrewAI docs: https://docs.crewai.com/
- Google A2A announcement: https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/
- A2A protocol docs: https://a2a-protocol.org/latest/
- A2A and MCP relation: https://a2a-protocol.org/latest/topics/a2a-and-mcp/
- ACP (i-am-bee) repository status: https://github.com/i-am-bee/acp
- Agent Client Protocol site (different ACP usage): https://agentclientprotocol.com/
- OPA docs: https://www.openpolicyagent.org/docs
- OPA FAQ: https://www.openpolicyagent.org/docs/faq
- OPA bundles: https://www.openpolicyagent.org/docs/management-bundles
- MCP introduction: https://modelcontextprotocol.io/docs/getting-started/intro
- MCP architecture: https://modelcontextprotocol.io/docs/learn/architecture
- Moonshot AI blog index: https://platform.moonshot.ai/blog
- Kimi context caching post: https://platform.moonshot.ai/blog/introducing-context-caching
- K2 API pricing post: https://platform.moonshot.ai/blog/kimi-k2-api-pricing

## 10. Notes on Evidence Strength
- High confidence areas: LangGraph capabilities, OPA role, MCP architecture, A2A positioning.
- Medium confidence areas: comparative adoption timing for AutoGen/CrewAI in this project context.
- Lower confidence area: precise Kimi K2.5 AgentSwarm cost/SLA efficiency for OpenQilin-specific workloads; requires controlled internal benchmark before hard commitment.
