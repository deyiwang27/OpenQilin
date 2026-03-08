# OpenQilin - Decision Review Gates Specification

## 1. Scope
- Defines mandatory review gates for project and budget decisions.

## 2. Gate Flow
- Proposal -> Strategic review -> Executive approval -> Initialization

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| GATE-001 | New projects MUST pass CSO strategic review before CEO approval. | high | Task Orchestrator |

## 4. Conformance Tests
- Proposal bypassing required gate is rejected.
