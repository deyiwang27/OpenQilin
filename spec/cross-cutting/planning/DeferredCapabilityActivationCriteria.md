# OpenQilin - Deferred Capability Activation Criteria Specification

## 1. Scope
- Defines activation gates for deferred/adopt_later capabilities.
- Ensures deferred capability adoption is policy-safe, cost-aware, and reversible.

## 2. Deferred Capability Set (Current)
- `Mem0` integration for assistive memory
- `OpenSearch` derived index
- managed `Redis` tier
- full managed/multi-node cloud runtime topology
- optional external owner channel expansions beyond Discord

## 3. Activation Gate Model
Every deferred capability requires:
- capability owner role
- activation proposal and rationale
- quantitative trigger evidence
- risk and rollback plan
- owner approval
- post-activation validation window

## 4. Capability Criteria

### 4.1 Mem0
- Activate when at least two conditions persist:
  - personalization memory requirements exceed current retrieval quality targets
  - operator cost of manual memory curation exceeds agreed threshold
  - governance controls for sensitive-memory filtering are validated
- Rollback:
  - disable Mem0 writes
  - keep authoritative state in relational source-of-record

### 4.2 OpenSearch
- Activate when at least two conditions persist:
  - lexical/hybrid retrieval latency or quality is below target with pgvector-only profile
  - observability search workloads exceed current exploratory query performance bounds
  - index operation overhead is justified by measured retrieval gain
- Rollback:
  - route retrieval back to baseline index path
  - rebuild optional index asynchronously

### 4.3 Managed Redis
- Activate when at least two conditions persist:
  - current Redis host presents unacceptable continuity risk
  - failover/SLO targets cannot be met by existing topology
  - operations burden exceeds team support capacity
- Rollback:
  - preserve snapshot and migration rollback path
  - fail closed for critical coordination paths during cutback

### 4.4 Full Managed Multi-Node Cloud
- Activate when at least two conditions persist:
  - sustained runtime resource pressure and queue/latency SLO breaches
  - RTO/RPO targets are not achievable with hybrid baseline
  - compliance, availability, or growth requirements exceed single-region baseline
- Rollback:
  - retain deployment interface compatibility
  - maintain tested restore path to previous topology

### 4.5 Additional Owner Channels
- Activate only after Discord model is stable and hardened.
- Required gates:
  - channel-specific identity/trust model specification
  - policy and audit mapping parity with Discord baseline
  - replay/idempotency and connector security validation
- Rollback:
  - disable external connector while preserving owner interaction audit history

## 5. Approval and Review
- proposal owner: `ceo` (or delegated architecture owner)
- approval authority: `owner`
- verification roles: `administrator`, `auditor`
- review cadence: per release cycle or on trigger breach

## 6. Normative Rule Bindings
- `BUD-001`: hard budget stops remain enforced during capability transitions.
- `POL-003`: activation and rollback failures are fail-closed for governed actions.
- `FRM-002`: recovery behavior remains deterministic under same policy version.
- `FRM-005`: capability activation/rollback actions emit immutable audit events.

## 7. Conformance Tests
- Capability cannot be activated without owner approval evidence.
- Activation without quantitative trigger evidence is rejected.
- Rollback procedures are documented and testable before activation.
