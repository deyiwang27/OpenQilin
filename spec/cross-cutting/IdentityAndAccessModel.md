# OpenQilin - Identity and Access Model Specification

## 1. Scope
- Defines agent identity, role binding, and access control boundaries.

## 2. Identity Model
- principal_id, role, credentials reference, trust domain

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| IAM-001 | Every runtime action MUST be attributable to an authenticated principal. | critical | Policy Engine |

## 4. Conformance Tests
- Unauthenticated action requests are denied.
