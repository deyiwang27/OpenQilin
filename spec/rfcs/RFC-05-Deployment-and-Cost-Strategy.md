# OpenQilin - RFC 05: Deployment and Cost Strategy

## 1. Scope
Domains in this RFC:
- Local deployment baseline with Docker
- Cloud deployment strategy for cost-efficiency
- Runtime topology choices for control plane, workers, and observability stack
- Cost model and scaling triggers
- Security and operations baseline for hosted environments

## 2. Investigation Questions
- What Docker topology should be the mandatory local/dev baseline (single-command reproducibility)?
- What cloud deployment pattern is most cost-efficient for early stage: single-node, managed services, or hybrid?
- Which components should be managed services vs self-hosted to minimize cost without harming reliability?
- What are the minimum backup/recovery and secret-management requirements for production readiness?
- What are the trigger points for scaling from low-cost baseline to higher-availability architecture?
- How should observability/storage retention settings be tuned for predictable spend?

## 3. Candidate Evaluation Matrix
| Domain | Candidate | Decision | Confidence | Conformance Impact | Notes |
| --- | --- | --- | --- | --- | --- |
| local/dev packaging | Docker | pending | pending | pending | pending |
| cloud runtime topology | low-cost baseline architecture | pending | pending | pending | pending |
| database hosting model | managed vs self-hosted PostgreSQL | pending | pending | pending | pending |
| cache/queue hosting model | managed vs self-hosted Redis | pending | pending | pending | pending |
| observability hosting | managed vs self-hosted telemetry stack | pending | pending | pending | pending |
| cost controls | budget and scaling policy | pending | pending | pending | pending |

## 4. Required Deliverables
- Local-first Docker reference topology with dev/CI parity guidance.
- Cloud deployment recommendation for early-stage cost-efficiency.
- Upgrade path from low-cost baseline to resilient multi-service architecture.
- Minimum security/backup/recovery control set.
- Adopt/defer decision per domain.
