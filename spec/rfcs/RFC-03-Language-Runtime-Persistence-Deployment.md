# OpenQilin - RFC 03: Runtime Interfaces and Operator Experience

## 1. Scope
Domains in this RFC:
- Python runtime and control plane implementation boundary
- Owner-agent communication channels (e.g., WhatsApp, Discord)
- Operator-facing experience via Grafana dashboards
- Custom UI option (TypeScript + React) only if required by unmet use cases
- Interface/API boundaries for channel connectors and operator tools

## 2. Investigation Questions
- Can v1 operate with channel-first interaction (WhatsApp/Discord) plus Grafana, without building a custom web app?
- What owner/operator use cases cannot be covered by channel integrations and Grafana, and therefore justify React?
- If React is needed, what is the minimum feature scope for v1 (admin console only vs full workbench)?
- Should TypeScript be limited to frontend/integration adapters while Python remains authoritative for runtime logic?
- What connector contract is required for message durability, identity mapping, auditability, and policy enforcement?

## 3. Candidate Evaluation Matrix
| Domain | Candidate | Decision | Confidence | Conformance Impact | Notes |
| --- | --- | --- | --- | --- | --- |
| control/runtime language | Python | pending | pending | pending | pending |
| owner communication channel | WhatsApp integration | pending | pending | pending | pending |
| owner communication channel | Discord integration | pending | pending | pending | pending |
| operator dashboard | Grafana | pending | pending | pending | pending |
| custom UI language | TypeScript | pending | pending | pending | pending |
| custom UI framework | React | pending | pending | pending | pending |
| connector/API boundary | FastAPI contracts | pending | pending | pending | pending |

## 4. Required Deliverables
- Owner interaction model decision: channel-first only vs channel + custom UI.
- Clear criteria for adopting/defering React in v1.
- Minimum connector contract (identity, delivery semantics, audit envelope, policy hooks).
- Adopt/defer decision per domain.
