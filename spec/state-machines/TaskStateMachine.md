# OpenQilin - Task State Machine Specification

## 1. Scope
- Canonical state machine for task execution flow.

## 2. States
- queued, authorized, dispatched, running, completed, failed, cancelled

## 3. Conformance Tests
- Denied authorization cannot transition to dispatched.
