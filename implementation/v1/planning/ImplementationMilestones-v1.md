# OpenQilin v1 - Implementation Milestones

## 1. Scope
- Convert the implementation backlog into milestone-level delivery slices.
- Lock the first executable slice for governance-core validation.

## 2. Planning Authority
- `design/TODO.txt` is a design-stage tracker and historical closeout record.
- GitHub Issues/PRs/Project are the authoritative implementation execution tracker.
- `implementation/v1/planning/ImplementationProgress-v1.md` is the in-repo milestone/status mirror.
- If implementation status differs, GitHub issue/PR evidence is authoritative and the progress mirror must be updated.

## 3. Milestones
### M0 Foundation Scaffold
Entry:
- design set closed and internally consistent

Exit:
- `uv` project initialized
- base package tree created
- Docker Compose baseline created
- CI skeleton running lint, type checks, and unit tests

### M1 First Executable Slice
Scope:
- API ingress
- task admission
- policy check
- budget reserve
- sandbox or LLM dispatch stub
- audit and trace emission

Exit:
- owner command accepted or blocked through governed path
- fail-closed paths verified for policy and budget uncertainty
- trace and audit evidence emitted end to end

### M2 Execution Targets
Scope:
- real sandbox dispatch
- real `llm_gateway` integration through LiteLLM
- basic retrieval-backed query path

Exit:
- governed dispatch reaches sandbox or Gemini-backed LLM path
- usage/cost metadata recorded
- retrieval query returns scoped results

### M3 Communication Reliability
Scope:
- A2A validation
- ACP send/ack/nack
- retries and dead-letter flow
- callback integration to orchestrator

Exit:
- at-least-once delivery path behaves deterministically
- duplicate deliveries avoid duplicate side effects
- dead-letter incidents emit alerts and audit evidence

### M4 Hardening and Release Readiness
Scope:
- dashboard and alerts
- migration validation and rollback checks
- conformance and smoke suites
- release artifact preparation

Exit:
- full compose profile admin-bootstrap smoke gate and conformance gates pass deterministically
- release candidate is promotable under manual gate for implemented runtime surface
- placeholder container replacement for `api_app` and workers is tracked as post-M4 hardening follow-up

## 4. First Executable Slice Detail
Recommended implementation order inside `M1`:
1. schema, migrations, and idempotency primitives
2. control-plane ingress envelope validation and identity binding
3. task admission and state persistence shell
4. policy normalization and decision path
5. budget reservation path
6. dispatch stub and observability emission

## 5. Blocking Rules
- Do not start communication reliability hardening before M1 governed path is stable.
- Do not start release hardening before M2 and M3 produce runnable end-to-end evidence.
