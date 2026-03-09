# OpenQilin - RFC 03: Language, Runtime, Persistence, and Deployment

## 1. Scope
Domains in this RFC:
- Python
- TypeScript
- React
- PostgreSQL
- Redis
- Docker

## 2. Investigation Questions
- What service boundaries are Python-first vs TypeScript-first?
- How should React UI integrate with control-plane and observability APIs?
- What persistence ownership split should exist between PostgreSQL and Redis?
- What Docker topology supports local reproducibility and CI parity?

## 3. Candidate Evaluation Matrix
| Domain | Candidate | Decision | Confidence | Conformance Impact | Notes |
| --- | --- | --- | --- | --- | --- |
| control/runtime language | Python | pending | pending | pending | pending |
| frontend language | TypeScript | pending | pending | pending | pending |
| frontend framework | React | pending | pending | pending | pending |
| source-of-record db | PostgreSQL | pending | pending | pending | pending |
| cache/queue/coordination | Redis | pending | pending | pending | pending |
| packaging/runtime | Docker | pending | pending | pending | pending |

## 4. Required Deliverables
- v1 service decomposition and language ownership map
- persistence model with failure/recovery implications
- deployment topology for local/dev/CI
- adopt/defer decision per domain
