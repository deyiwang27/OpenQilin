# OpenQilin - Spec and Constitution Release Checklist

## 1. Scope
- Defines pre-merge and pre-release documentation gates for `spec/` and `constitution/`.
- Applies to governance-core and contract-bearing documentation changes.

## 2. Pre-Merge Checklist
- Index integrity:
  - new/renamed docs are reflected in `spec/README.md` and/or `constitution/README.md`
  - removed docs are removed from indexes
- Role consistency:
  - canonical role names match across authority matrix, policy manifest, and spec contracts
- Constitution manifest consistency:
  - `PolicyManifest.yaml` required files align with actual constitutional policy files
  - runtime manifest and release record contracts are both satisfied for versioned snapshots
- Rule linkage:
  - changed rule statements are reflected in registry and coverage artifacts, or explicitly deferred with rationale
- RFC decision carry-through:
  - adopted decisions are reflected in normative specs (not RFC-only)

## 3. Pre-Release Checklist
- Conformance artifacts freshness:
  - `RuleRegistry.json` and `ConformanceCoverage.json` regenerated and reviewed
- Governance contract consistency:
  - policy, escalation, budget, and authority contracts are mutually consistent
- Documentation precedence integrity:
  - no lower-precedence docs contradict constitutional constraints
- Deferred capability clarity:
  - deferred/adopt_later features have explicit activation criteria
- Release evidence:
  - checklist completion evidence recorded with release metadata
  - `constitution/versions/<version>/ReleaseRecord.yaml` present and aligned to runtime manifest (`policy_version`, `bundle_hash`)

## 4. Gate Outcome States
- `pass`: all required checks complete with no unresolved blocking issues.
- `conditional_pass`: non-blocking issues documented with owner-approved follow-up.
- `fail`: one or more blocking checks fail; release is blocked.

## 5. Blocking Conditions
- unresolved role-name mismatch across constitutional and runtime contracts
- stale rule registry/coverage for changed rule-bearing docs
- missing constitutional file listed as required in manifest
- unresolved P0 documentation backlog items

## 6. Normative Rule Bindings
- `TEST-001`: critical rules require conformance mappings.
- `TEST-002`: integrity checks pass before merge/release.
- `TEST-004`: constitution/spec role and authority mappings remain consistent.
- `RID-002`: canonical rule-id references resolve in registry.
- `RID-004`: integrity validation fails on unresolved references.

## 7. Conformance Tests
- A release-candidate doc set with stale registry artifacts fails this checklist.
- Role mismatch between constitution and spec blocks release.
- Missing manifest-required constitutional policy file blocks release.
