# OpenQilin - RFC 02: Memory, Intelligence, and Observability

## 1. Scope
Domains in this RFC:
- LLM gateway and model routing: LiteLLM
- Retrieval architecture: RAG
- Capability packaging: Skills
- Memory layer: Mem0
- Vector index: pgvector
- Search index: OpenSearch
- Telemetry baseline: OpenTelemetry
- Tracing/evaluation overlay: LangSmith
- Ops/cost overlay: AgentOps
- Dashboarding and alerting: Grafana

Timebox:
- Spike (documentation and architecture decision only)
- Date: 2026-03-09

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
| llm gateway | LiteLLM | adopt (v1 default gateway) | high | strong positive | Unified provider API + routing/fallback + budget controls align with governance budget gates. |
| retrieval | RAG | adopt (grounded generation baseline) | high | strong positive | Use constrained RAG profile with citation/provenance and deterministic retrieval settings. |
| capability packaging | Skills | adopt (internal spec artifact) | medium | positive | Treat as policy-governed capability contracts, mapped to allowed tools/models. |
| memory layer | Mem0 | adopt_later (optional integration, not source-of-record) | medium | positive | Useful layered/graph memory features; keep authoritative state in project data model first. |
| vector index | pgvector | adopt (v1 default) | high | positive | Co-locate vectors with Postgres source data for simpler operations and consistency. |
| search/index | OpenSearch | adopt_later (derived index, selective use) | medium | neutral-positive | Best for large-scale lexical/hybrid search and observability exploration; avoid dual-writes as source-of-record. |
| telemetry baseline | OpenTelemetry | adopt (mandatory baseline) | high | strong positive | Vendor-neutral telemetry + Collector pipeline must be default. |
| tracing overlay | LangSmith | adopt (system tracing and evaluation overlay) | medium-high | positive | User decision: keep in active system stack. |
| ops/cost overlay | AgentOps | adopt (system cost and operations overlay) | medium | positive | User decision: keep in active system stack. |
| dashboarding | Grafana | adopt (standard dashboards + alerts) | high | positive | Natural fit for OTel data and operational alerting. |

## 4. Spike Findings and Decisions

### 4.1 LiteLLM as Gateway
Decision:
- Adopt LiteLLM as the v1 LLM gateway boundary.

Why:
- LiteLLM exposes a unified model interface, router-based load balancing, retries/fallbacks, and budget/rate-limit controls.
- Gateway mode supports centralized spend governance and multi-tenant controls, which maps well to OpenQilin policy gates.

v1 integration boundary:
- Orchestrator never calls providers directly.
- All model calls pass through LiteLLM with:
  - budget thresholds and soft/hard enforcement
  - explicit fallback policy
  - request metadata for cost attribution (agent, task, project)
  - audit event emission on fallback and budget-crossing outcomes

### 4.2 RAG vs Structured Memory
Decision:
- Adopt a dual model: constrained RAG for external/domain knowledge, structured memory for agent/session/user state.

Why:
- RAG is effective for knowledge-intensive tasks when parametric generation is combined with non-parametric retrieval.
- Structured memory must remain separate from generic retrieval to preserve deterministic workflow state and policy control.

v1 retrieval profile:
- Pin chunking strategy + embedding model version.
- Require provenance/citations in generation context.
- Keep retrieval parameters (k, rerank policy, filters) policy-configurable.
- Fail safe: when retrieval is unavailable, route to non-RAG response mode with explicit reduced-confidence metadata.

### 4.3 Skills Model
Decision:
- Adopt Skills as internal capability packaging (YAML/structured spec), not as transport protocol.

Model:
- Skill defines intent, allowed tool set, allowed model classes, safety constraints, budget class, and escalation obligations.
- Runtime resolution: `skill -> policy check -> tool/model invocation`.

Rationale:
- There is no single cross-vendor “skills” runtime standard equivalent to MCP for tool transport.
- Keeping Skills as an internal governance artifact preserves portability and control.

### 4.4 Mem0 Positioning
Decision:
- Keep Mem0 as adopt_later/optional integration for personalization memory acceleration.
- Do not treat Mem0 as source-of-record in v1.

Why:
- Mem0’s layered memory model (conversation/session/user/org) and graph augmentation are useful.
- Governance-critical state should remain in OpenQilin’s authoritative stores and schemas first.

v1 boundary:
- Authoritative state: project-owned datastore/schema.
- Derived/assistive memory: optional Mem0 sync path behind CDC + policy filters.
- PII/secrets controls apply before any long-term memory write.

### 4.5 pgvector + OpenSearch Split
Decision:
- Adopt pgvector as v1 default vector index.
- Use OpenSearch later as selective derived index for:
  - large-scale lexical/hybrid retrieval workloads
  - observability search and exploration

Why:
- pgvector keeps embeddings with transactional data in Postgres, simplifying consistency and operations at early stage.
- OpenSearch is powerful for search/observability scale but introduces additional operational surface; use where it clearly pays off.

Data model rule:
- Single source-of-record; indexes are rebuildable derivatives.
- No business-critical dual-write without replay and reconciliation guarantees.

### 4.6 Observability Stack: OTel Baseline + System Overlays
Decision:
- OpenTelemetry is mandatory baseline.
- Grafana is mandatory operational dashboard/alert layer.
- LangSmith is retained in system for LLM trace/eval workflows.
- AgentOps is retained in system for cost/ops analytics.

Why:
- OTel provides vendor-neutral instrumentation and Collector-based processing pipelines.
- Grafana integrates well for traces/metrics/logs and alert workflows.
- LangSmith and AgentOps provide complementary LLM trace + cost/ops overlays when scoped by clear responsibility boundaries.

## 5. Reference Architecture (v1)

### 5.1 Memory and Retrieval Model
- Source-of-record:
  - relational task/project/agent state
  - policy/audit metadata
- Derived indexes:
  - pgvector index (default)
  - OpenSearch index (optional later)
- Optional memory accelerator:
  - Mem0 adapter (non-authoritative)

### 5.2 Intelligence Flow
1. Orchestrator resolves skill and policy envelope.
2. Retrieve context from structured memory + RAG indexes.
3. Call LiteLLM gateway with budget/routing constraints.
4. Emit OTel spans/metrics/logs + audit events.
5. Persist result and derived memory updates through controlled write path.

### 5.3 Observability Layering
- Mandatory:
  - OTel instrumentation + Collector
  - Grafana dashboards + alerts
- System overlays:
  - LangSmith (trace debugging/evaluation)
  - AgentOps (cost and operational analytics)

## 6. Cost and Safety Profile
- LiteLLM: improves provider routing/fallback and budget controls; adds gateway operational cost.
- RAG: improves factual grounding; increases retrieval infra and indexing costs.
- pgvector: low operational complexity in Postgres-first architecture.
- OpenSearch: high search flexibility and scale; higher infra/ops cost.
- OTel+Grafana: strong baseline observability; requires disciplined telemetry cardinality management.
- Overlay tools: improve AI-specific diagnostics but can duplicate ingestion and spend if not scoped.

## 7. Failure and Security Risks
- Risk: retrieval drift due to index/schema/version mismatch.
- Mitigation: version all chunking/embedding/index pipelines and include retrieval version in trace metadata.

- Risk: budget bypass through direct provider calls.
- Mitigation: enforce egress policy so only LiteLLM gateway can reach providers.

- Risk: sensitive data leakage into long-term memory.
- Mitigation: redaction/classification policy before memory promotion; deny writes for blocked classes.

- Risk: observability fragmentation across multiple overlays.
- Mitigation: OTel as canonical telemetry substrate; overlays consume from defined integration points.

## 8. Recommendation Summary
Adopt now:
- LiteLLM
- RAG (constrained profile)
- Skills (internal policy-governed packaging)
- pgvector
- OpenTelemetry
- Grafana
- LangSmith
- AgentOps

Adopt later / optional:
- Mem0 (assistive memory layer)
- OpenSearch (derived search/observability index where justified)

## 9. Migration / Rollback Notes
- If LiteLLM gateway introduces instability, keep provider adapters behind one internal interface so gateway can be swapped without orchestrator contract changes.
- If RAG quality regresses, disable retrieval per skill and run parametric-only mode while preserving provenance flags.
- If OpenSearch is added and underperforms, keep pgvector path as baseline and disable OpenSearch-derived retrieval routes.
- If overlay observability tools create noise/cost, retain OTel+Grafana baseline and disable overlay exporters.

## 10. Sources (Primary)
- LiteLLM getting started and gateway overview: https://docs.litellm.ai/docs/
- LiteLLM budgets/rate limits: https://docs.litellm.ai/docs/proxy/users
- LiteLLM budget routing: https://docs.litellm.ai/docs/proxy/provider_budget_routing
- LiteLLM router/load balancing: https://docs.litellm.ai/docs/routing
- LiteLLM fallbacks/reliability: https://docs.litellm.ai/docs/proxy/reliability

- RAG foundational paper: https://arxiv.org/abs/2005.11401

- Mem0 memory layers: https://docs.mem0.ai/core-concepts/memory-types
- Mem0 graph memory: https://docs.mem0.ai/open-source/features/graph-memory

- pgvector official repository/docs: https://github.com/pgvector/pgvector

- OpenSearch vector search docs: https://docs.opensearch.org/2.16/search-plugins/vector-search/
- OpenSearch vector search API: https://docs.opensearch.org/latest/vector-search/api/index/
- OpenSearch observability docs: https://docs.opensearch.org/platform/observability/

- OpenTelemetry docs overview: https://opentelemetry.io/docs/
- OpenTelemetry Collector: https://opentelemetry.io/docs/collector/
- OpenTelemetry GenAI semantic conventions: https://opentelemetry.io/docs/specs/semconv/gen-ai/

- LangSmith observability: https://docs.langchain.com/langsmith/observability
- LangSmith platform setup modes: https://docs.langchain.com/langsmith/platform-setup

- AgentOps quickstart: https://docs.agentops.ai/v2/quickstart
- AgentOps TypeScript SDK: https://docs.agentops.ai/v2/usage/typescript-sdk

- Grafana OpenTelemetry docs: https://grafana.com/docs/opentelemetry/
- Grafana alert list docs: https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/visualizations/alert-list/

- Semantic Kernel plugin model (skills packaging reference): https://learn.microsoft.com/en-us/semantic-kernel/agents/plugins/

## 11. Evidence Strength Notes
- High confidence: LiteLLM gateway capabilities, OTel baseline role, pgvector fit for Postgres-first architecture.
- Medium confidence: OpenSearch timing for early-stage adoption and exact LangSmith/AgentOps boundary tuning under real workloads.
- Medium-low confidence: exact cost-performance crossover point for introducing OpenSearch and multiple observability overlays; requires workload-specific benchmark in later implementation baseline.

## 12. User Comment Overrides (2026-03-09)
- Owner decision: keep both `LangSmith` and `AgentOps` in the active system stack.
- This override supersedes the earlier spike recommendation that deferred AgentOps and treated LangSmith as optional.
