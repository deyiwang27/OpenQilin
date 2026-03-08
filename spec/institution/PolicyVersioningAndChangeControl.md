# OpenQilin - Policy Versioning and Change Control Specification

## 1. Scope
- Defines policy lifecycle, approval, rollout, and rollback controls.

## 2. Versioning Rules
- Semantic versioning for policy bundles
- Backward-incompatible policy change requires major bump

## 3. Change Control Workflow
- Propose -> impact review -> approval -> publish -> snapshot

## 4. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| PVC-001 | Runtime decisions MUST include policy version and hash. | critical | Policy Engine |

## 5. Conformance Tests
- Rollback to prior policy version preserves decision reproducibility.
