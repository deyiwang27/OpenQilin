# OpenQilin - Execution Sandbox Specification

## 1. Scope
- Isolated environment for tool/code execution with safety controls.

## 2. Isolation Controls
- Filesystem, network, process, timeout, resource quotas

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| SAN-001 | Sandbox MUST enforce per-task resource quotas. | critical | Execution Sandbox |
| SAN-002 | Forbidden capabilities MUST fail closed. | critical | Execution Sandbox |

## 4. Conformance Tests
- Quota breach terminates execution safely.
