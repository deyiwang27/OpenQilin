# OpenQilin - Agent Authority Graph Specification

## 1. Scope
- Defines authority types and role-to-authority mapping.

## 2. Canonical Authorities
- Decision, Command, Execution, Review, Advisory, Oversight, Workforce

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| AUTH-001 | Actions outside authority matrix MUST be denied. | critical | Policy Engine |

## 4. Data Contract
- Authority check request/response schema references PolicyEngine contract.

## 5. Conformance Tests
- Invalid role-action-target triplets are denied.
