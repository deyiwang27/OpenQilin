# OpenQilin - Conformance Test Plan Specification

## 1. Scope
- Defines cross-spec conformance strategy and release gates.

## 2. Test Categories
- policy enforcement
- orchestration behavior
- safety containment
- budget enforcement
- observability completeness
- observability stack alignment (OpenTelemetry baseline + LangSmith/AgentOps overlays)
- state-machine transition integrity
- communication protocol correctness (A2A + ACP)
- deployment promotion integrity (local-first gates before cloud phase)

## 3. Conformance Artifacts
- Rule registry: `spec/cross-cutting/RuleRegistry.json`
- Coverage mapping: `spec/cross-cutting/ConformanceCoverage.json`
- Integrity checklist: path references resolve and all referenced rule IDs are present in rule registry.

## 4. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| TEST-001 | Critical rules MUST have at least one conformance mapping in coverage artifacts. | critical | ci_pipeline |
| TEST-002 | Spec integrity checks MUST pass before merge/release. | critical | ci_pipeline |
| TEST-003 | State machine specs MUST be consistent with orchestration/runtime contracts. | high | spec_review |
| TEST-004 | Constitution/spec role and authority mappings MUST remain consistent. | high | spec_review |
| TEST-005 | Tool investigation RFCs MUST record adopt/defer decisions before architecture baseline lock. | high | governance_review |

## 5. Release Gate
- No release if any critical conformance checks fail.
- No release if rule registry and coverage artifacts are outdated.
- No release if unresolved P0 TODO items remain.
- No cloud promotion if phase_0 local readiness gates are incomplete.
