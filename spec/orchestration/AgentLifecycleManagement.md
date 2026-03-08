# OpenQilin - Agent Lifecycle Management Specification

## 1. Scope
- Defines lifecycle states and transitions for project and specialist agents.

## 2. States
- created, active, paused, retired, archived

## 3. Transition Rules
| From | Event | Guard | To |
| --- | --- | --- | --- |
| created | activate | authorization=allow | active |
| active | pause | governance_or_pm_request | paused |
| paused | resume | authorization=allow | active |
| active | retire | task_complete | retired |
| retired | archive | retention_elapsed | archived |

## 4. Conformance Tests
- Invalid transitions are rejected.
