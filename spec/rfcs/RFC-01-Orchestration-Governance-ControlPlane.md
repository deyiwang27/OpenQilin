# OpenQilin - RFC 01: Orchestration, Governance, and Control Plane

## 1. Scope
Domains in this RFC:
- LangGraph
- AgentSwarm
- A2A + ACP interoperability model
- Open Policy Agent (OPA)
- FastAPI
- FastMCP

## 2. Investigation Questions
- Can LangGraph act as canonical orchestrator while preserving deterministic governance gates?
- Should AgentSwarm remain external/optional in v1, and what invocation boundary is safe?
- How should ACP be layered over A2A for runtime transport guarantees?
- Should OPA be authoritative policy runtime now or introduced after v1 baseline?
- What is the correct control-plane split between FastAPI and FastMCP?

## 3. Candidate Evaluation Matrix
| Domain | Candidate | Decision | Confidence | Conformance Impact | Notes |
| --- | --- | --- | --- | --- | --- |
| orchestration | LangGraph | pending | pending | pending | pending |
| external parallel runtime | AgentSwarm | pending | pending | pending | pending |
| policy runtime | OPA | pending | pending | pending | pending |
| API layer | FastAPI | pending | pending | pending | pending |
| MCP tool bridge | FastMCP | pending | pending | pending | pending |
| protocol composition | A2A + ACP | pending | pending | pending | pending |

## 4. Required Deliverables
- reference architecture diagram (control plane + data plane)
- fail-closed decision path under policy/runtime failure
- recommended implementation sequence
- adopt/defer decision per domain
