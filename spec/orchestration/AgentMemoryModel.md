# OpenQilin - Agent Memory Model Specification

## 1. Scope
- Defines memory tiers, access scopes, and retrieval/write constraints.

## 2. Tiers
- Hot, Warm, Cold

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| MEM-001 | Immutable execution logs MUST be append-only. | critical | Observability |

## 4. Conformance Tests
- Unauthorized memory access is denied and logged.
