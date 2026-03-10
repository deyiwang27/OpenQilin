# OpenQilin - Constitution Binding Model Specification

## 1. Scope
- Defines how runtime components bind and enforce constitutional artifacts.
- Defines startup load, validation, activation, and reload semantics for constitutional policy.

## 2. Binding Model
- Policy source format: YAML only.
- Static load at startup.
- Hot reload only on approved and published version change.
- Single globally active version pointer.
- Runtime must fail-closed if policy cannot be loaded/validated.
- `constitution/core/PolicyManifest.yaml` is the runtime source of truth for required artifact membership.

## 3. Bound Artifacts (v1)
The runtime bundle MUST bind all artifacts listed in `policy_bundle.required_files` from `constitution/core/PolicyManifest.yaml`.

Canonical v1 artifact set:
- `core/AuthorityMatrix.yaml`
- `core/PolicyRules.yaml`
- `core/ObligationPolicy.yaml`
- `domain/EscalationPolicy.yaml`
- `domain/BudgetPolicy.yaml`
- `domain/SafetyPolicy.yaml`
- `domain/OperationsPolicy.yaml`

## 4. Validation Pipeline
1. Parse `PolicyManifest.yaml` and resolve `policy_bundle.required_files`.
2. Verify every required artifact exists under `constitution/`.
3. Parse all required YAML artifacts.
4. Validate schema and required keys.
5. Validate cross-file references (rule IDs, roles, thresholds).
6. Compute bundle hash.
7. Activate version only if all checks pass.

## 5. Runtime Binding Output
Every policy decision context must include:
- `policy_version`
- `policy_hash`
- `rule_ids` used in decision

## 6. Failure Behavior
- Any parse/validation/load error -> deny by default (fail-closed).
- If no valid active policy exists, execution must halt for policy-protected actions.

## 7. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| CBM-001 | Policy evaluation MUST use an explicit constitution version. | critical | Policy Engine |
| CBM-002 | Only YAML policy artifacts are accepted in v1. | high | Constitution Binding |
| CBM-003 | Global active policy version MUST be singular and atomically switchable. | critical | Constitution Binding |
| CBM-004 | Invalid policy bundle activation MUST fail-closed. | critical | Constitution Binding |

## 8. Conformance Tests
- Action decision records include constitution version and rule IDs.
- Missing any file declared in `policy_bundle.required_files` blocks activation.
- Invalid YAML blocks activation.
- Cross-file reference errors block activation.
- Active version switch is atomic and auditable.
