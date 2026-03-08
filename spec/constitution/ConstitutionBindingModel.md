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

## 3. Bound Artifacts (v1)
- `AuthorityMatrix.yaml`
- `PolicyRules.yaml`
- `EscalationPolicy.yaml`
- `BudgetPolicy.yaml`
- `SafetyPolicy.yaml`

## 4. Validation Pipeline
1. Parse YAML artifacts.
2. Validate schema and required keys.
3. Validate cross-file references (rule IDs, roles, thresholds).
4. Compute bundle hash.
5. Activate version only if all checks pass.

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
- Invalid YAML blocks activation.
- Cross-file reference errors block activation.
- Active version switch is atomic and auditable.
