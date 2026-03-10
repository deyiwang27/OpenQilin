# OpenQilin - RFC 03: Runtime Interfaces and Operator Experience

## 1. Scope
Domains in this RFC:
- Python runtime and control-plane boundary
- Owner-agent communication channels (Discord and WhatsApp)
- Operator-facing experience via Grafana
- Custom UI path (TypeScript + React) only if required by unmet v1 use cases
- Connector/API contract for identity, durability, policy, and audit

Timebox:
- Spike (documentation and architecture decision only)
- Date: 2026-03-09

## 2. Investigation Questions
- Can v1 run channel-first (chat channels + Grafana) without custom React UI?
- Which owner/operator workflows are not covered by channel-first + Grafana?
- Should TypeScript/React be deferred until those workflow gaps are proven?
- Should Python remain authoritative runtime language for core services?
- What connector contract is required for reliability, identity mapping, policy gates, and immutable audit trails?

## 3. Candidate Evaluation Matrix
| Domain | Candidate | Decision | Confidence | Conformance Impact | Notes |
| --- | --- | --- | --- | --- | --- |
| control/runtime language | Python | adopt (v1 default) | high | strong positive | Async IO ecosystem and FastAPI fit control-plane and connector services. |
| connector/API boundary | FastAPI contracts | adopt | high | strong positive | OpenAPI-first contracts with security tooling and typed request validation. |
| owner communication channel | Discord integration | adopt (v1 primary) | high | positive | Mature interaction/webhook model and clear command registration flow. |
| owner communication channel | WhatsApp Cloud API integration | adopt_later (optional v1.1+) | medium-low | neutral-positive | Strong business channel, but onboarding/policy/pricing model adds rollout friction. |
| operator dashboard | Grafana | adopt (ops dashboard + alert routing) | high | positive | Rich dashboards, alerting contact points, webhooks, sharing, RBAC controls. |
| custom UI language | TypeScript | defer for v1 core; adopt_later if custom UI required | high | neutral | Keep TypeScript scope to UI/integration adapters only when justified. |
| custom UI framework | React | defer for v1; adopt_later with explicit trigger criteria | high | neutral | React is ideal for custom UI, but channel-first + Grafana likely sufficient initially. |

## 4. Spike Findings and Decisions

### 4.1 Python + FastAPI Runtime Boundary
Decision:
- Adopt Python as the authoritative runtime language for v1 control plane.
- Adopt FastAPI as the connector and control-plane API boundary.

Rationale:
- Python `asyncio` is designed for concurrent IO-heavy services and is a common base for networked async frameworks.
- FastAPI provides OpenAPI-native API generation and built-in security utilities, supporting a contract-first governance model.

Boundary rule:
- Core policy/orchestration/connector logic stays Python-first.
- Any non-Python adapter must call stable FastAPI contracts rather than embedding governance logic.

### 4.2 Channel-First Owner Interaction
Decision:
- Adopt Discord as v1 primary owner-agent interactive channel.
- Keep WhatsApp as optional follow-on integration (adopt_later), not required for v1 baseline.

Discord findings:
- Interactions can be received either by gateway events or outgoing webhook, and those methods are mutually exclusive.
- Application commands are registered via HTTP endpoints and do not require a bot scope for all use cases.
- Official Discord tooling shows request-signature verification with `X-Signature-Ed25519` and `X-Signature-Timestamp`.

WhatsApp findings:
- Meta’s official Cloud API is suitable for business messaging at scale with agent/bot patterns.
- Access requires business onboarding assets and permission setup (`whatsapp_business_management`, `whatsapp_business_messaging`), plus access-token lifecycle management.
- Direct crawling of `developers.facebook.com/docs/whatsapp/*` was rate-limited (HTTP 429) in this spike, so confidence on policy/pricing edge details is lower and needs explicit validation before production commitment.

### 4.3 Grafana as Operator Experience
Decision:
- Adopt Grafana for v1 operator observability and alert routing.

Rationale:
- Grafana contact points + notification policies + webhook notifications support routing platform events to operational channels.
- Dashboard sharing and RBAC/permissions APIs support controlled visibility for operators and stakeholders.

Scope boundary:
- Grafana is for observability and incident operations, not for full transactional workflow UI (e.g., complex approval forms/workbenches).

### 4.4 React/TypeScript Decision Criteria
Decision:
- Defer React and TypeScript for v1 custom UI unless trigger criteria are met.

Trigger criteria (any 2 justify adoption):
- Need multi-step approval workflows that are inefficient in chat channels.
- Need rich stateful investigations across entities (task/memory/policy/audit) in one workspace.
- Need high-density operational controls beyond Grafana and chat command ergonomics.
- Need delegated role-specific workbenches with advanced navigation and bulk actions.

Minimum scope if adopted:
- Admin/operations console only (identity, policy status, run control, audit lookup), not full end-user product surface.

## 5. Recommended v1 Interface Architecture
Ingress channels:
- Discord interaction webhook endpoint (primary).
- Optional WhatsApp adapter endpoint (feature-flagged).

Core services:
- FastAPI endpoints for command ingestion, event query, and operator actions.
- Python orchestration + policy evaluation + budget gates as authoritative execution path.

Ops surface:
- Grafana dashboards + alert routing (webhook/contact points).

Optional UI:
- React/TypeScript admin console only after trigger criteria are met.

## 6. Minimum Connector Contract (v1)
Every inbound command/event from external channel must include or derive:
- `channel` (`discord|whatsapp|...`)
- `external_message_id`
- `trace_id`
- `received_at` (RFC3339)
- `actor_external_id`
- `actor_internal_role` (resolved by identity map)
- `project_id` (optional for global commands)
- `command_type`
- `idempotency_key`
- `raw_payload_hash`

Enforcement requirements:
- Verify platform signature/token before parsing payload.
- Resolve external identity to internal role before policy checks.
- Run policy and budget gates before any execution-capable action.
- Emit immutable audit event for accepted and denied high-impact actions.
- Use idempotency key to prevent duplicate side effects on retries/redelivery.

## 7. Cost and Operational Profile
- Channel-first + Grafana is lower cost and faster to launch than building/maintaining a custom UI from day one.
- Discord integration is low-friction for engineering/operator workflows.
- WhatsApp introduces additional onboarding, permission, and token-management operations; adopt where business reach justifies it.
- Deferring React/TypeScript avoids premature frontend platform cost.

## 8. Risks and Mitigations
- Risk: Channel payload spoofing or replay.
- Mitigation: strict signature verification, timestamp checks, replay window, idempotency store.

- Risk: Chat channel UX limits for complex governance operations.
- Mitigation: define trigger criteria and escalate to minimal React admin console only when needed.

- Risk: Platform policy/pricing drift (especially WhatsApp).
- Mitigation: pin integration to versioned connector contracts and run pre-production compliance checks on each provider update.

- Risk: Operator blind spots if relying on chat alone.
- Mitigation: Grafana dashboards + alert routing mandatory in baseline.

## 9. Recommendation Summary
Adopt now:
- Python runtime
- FastAPI connector/control-plane contracts
- Discord integration (primary owner-agent channel)
- Grafana for observability and alert routing

Adopt later / optional:
- WhatsApp Cloud API integration
- TypeScript + React custom admin console (only if trigger criteria are met)

Defer:
- Full custom frontend product surface in v1

## 10. Sources (Primary)
- Python `asyncio` docs: https://docs.python.org/3.13/library/asyncio.html
- FastAPI home: https://fastapi.tiangolo.com/
- FastAPI security tutorial: https://fastapi.tiangolo.com/tutorial/security/
- FastAPI background tasks reference: https://fastapi.tiangolo.com/reference/background/

- Discord receiving/responding interactions: https://discord.com/developers/docs/interactions/receiving-and-responding
- Discord application commands: https://docs.discord.com/developers/interactions/application-commands
- Discord gateway docs: https://docs.discord.com/developers/events/gateway
- Discord API reference: https://docs.discord.com/developers/reference
- Official Discord interactions helper repo: https://github.com/discord/discord-interactions-js

- Grafana contact points: https://grafana.com/docs/grafana/latest/alerting/fundamentals/notifications/contact-points/
- Grafana webhook notifier: https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/webhook-notifier/
- Grafana share dashboards and panels: https://grafana.com/docs/grafana/latest/visualizations/dashboards/share-dashboards-panels/
- Grafana externally shared dashboards: https://grafana.com/docs/grafana/latest/dashboards/share-dashboards-panels/shared-dashboards/
- Grafana dashboard permissions: https://grafana.com/docs/grafana/latest/permissions/dashboard_folder_permissions/
- Grafana dashboard permissions HTTP API: https://grafana.com/docs/grafana/latest/developers/http_api/dashboard_permissions/

- React installation and gradual adoption: https://react.dev/learn/installation
- React quick start: https://react.dev/learn
- TypeScript official overview: https://www.typescriptlang.org/
- TypeScript JS project strictness ladder: https://www.typescriptlang.org/docs/handbook/intro-to-js-ts.html

- Meta official WhatsApp Cloud API collection (Meta Postman): https://www.postman.com/meta/whatsapp-business-platform/collection/wlk6lh4/whatsapp-cloud-api
- Referenced official docs from Meta collection:
  - https://developers.facebook.com/docs/whatsapp/cloud-api/overview
  - https://developers.facebook.com/docs/whatsapp/cloud-api/get-started
  - https://developers.facebook.com/docs/whatsapp/pricing/

## 11. Evidence Strength Notes
- High confidence: Python/FastAPI boundary, Discord-first integration pattern, Grafana for observability and alerts, React/TypeScript defer criteria.
- Medium confidence: exact point where chat-channel-only UX becomes insufficient for your operator workflow.
- Medium-low confidence: WhatsApp policy/pricing edge behavior in this spike, because direct crawling of `developers.facebook.com/docs/whatsapp/*` was rate-limited and had to be cross-checked via Meta’s official Postman collection references.
