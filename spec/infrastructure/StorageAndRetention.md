# OpenQilin - Storage and Retention Specification

## 1. Scope
- Defines storage classes, retention windows, archival policy, and retrieval constraints.

## 2. Storage Classes
- operational, audit, archive

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| STR-001 | Audit data MUST be immutable and retained per policy. | critical | Administrator |

## 4. Conformance Tests
- Expired operational data follows retention transition policy.
