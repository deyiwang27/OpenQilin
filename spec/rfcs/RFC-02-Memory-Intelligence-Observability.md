# OpenQilin - RFC 02: Memory, Intelligence, and Observability

## 1. Scope
Domains in this RFC:
- LiteLLM
- RAG
- Skills
- Mem0
- pgvector
- OpenSearch
- OpenTelemetry
- LangSmith
- AgentOps
- Grafana

## 2. Investigation Questions
- What gateway architecture should LiteLLM own in v1 (routing, fallback, cost guardrails)?
- What retrieval split between RAG and structured memory is required for deterministic behavior?
- How should skills be packaged/versioned and bound to policy/tool authorization?
- Where should Mem0 sit relative to source-of-record + CDC + vector index?
- Should OpenSearch be search index only, observability index, or both?
- What observability baseline must be mandatory (OpenTelemetry) vs optional overlays (LangSmith/AgentOps)?

## 3. Candidate Evaluation Matrix
| Domain | Candidate | Decision | Confidence | Conformance Impact | Notes |
| --- | --- | --- | --- | --- | --- |
| llm gateway | LiteLLM | pending | pending | pending | pending |
| retrieval | RAG | pending | pending | pending | pending |
| capability packaging | Skills | pending | pending | pending | pending |
| memory layer | Mem0 | pending | pending | pending | pending |
| vector index | pgvector | pending | pending | pending | pending |
| search/index | OpenSearch | pending | pending | pending | pending |
| telemetry baseline | OpenTelemetry | pending | pending | pending | pending |
| tracing overlay | LangSmith | pending | pending | pending | pending |
| ops/cost overlay | AgentOps | pending | pending | pending | pending |
| dashboarding | Grafana | pending | pending | pending | pending |

## 4. Required Deliverables
- memory and retrieval reference model (source-of-record + derived indexes)
- observability stack baseline/optional layering decision
- cost profile with safety tradeoffs
- adopt/defer decision per domain
