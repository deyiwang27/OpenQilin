# OpenQilin - Identity and Access Model Specification

## 1. Scope
- Defines agent identity, role binding, and access control boundaries.
- Defines mapping between external channel identities and internal governed principals.
- Defines v1 external channel hardening posture for Discord integration.
- Channel-specific controls are detailed in `spec/cross-cutting/security/DiscordOwnerChannelIdentityHardening.md`.

## 2. Identity Model
Canonical identity fields:
- `principal_id`
- `principal_type` (`human|agent|system_connector`)
- `role`
- `credentials_ref`
- `trust_domain`
- `status`
- `created_at`
- `updated_at`

External mapping fields:
- `channel`
- `actor_external_id`
- `mapped_principal_id`
- `verification_state`
- `last_verified_at`

## 3. Access Model
- Role and scope authorization is evaluated by policy engine.
- Cross-project access requires explicit project scope authorization.
- External identities are denied by default until mapped and verified.
- Connector-authenticated requests still require policy authorization.
- v1 channel hardening profile is Discord-only; additional channels are deferred.

## 4. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| IAM-001 | Every runtime action MUST be attributable to an authenticated principal. | critical | Policy Engine |

## 5. Conformance Tests
- Unauthenticated action requests are denied.
- Unknown external identity mappings are denied.
- Disabled principal cannot invoke runtime actions.
