# OpenQilin - Discord Owner Channel and Identity Hardening Specification

## 1. Scope
- Defines Discord-first security and identity controls for owner-agent interactions.
- Applies to v1 external channel integration profile (Discord only).

## 2. Integration Boundary
- Supported channel: Discord.
- Supported interaction modes:
  - owner direct messages to allowed roles
  - owner participation in authorized group/project/executive channels
- Unsupported in v1:
  - WhatsApp and other external channels in production path

## 3. Identity Mapping Model
- External identity tuple:
  - `channel=discord`
  - `actor_external_id` (Discord user id)
  - `server_id` (guild id, when applicable)
  - `channel_id`
- Mapping requirements:
  - external identity must map to one internal principal
  - mapping state must be explicit (`verified|revoked|pending`)
  - revoked mappings are fail-closed denied

## 4. Channel Trust and Access Controls
- Allowlist controls:
  - approved guild ids
  - approved channel ids per interaction class
- Role/scope controls:
  - channel message processing must pass policy authorization
  - cross-project or out-of-scope channel access is denied
- High-impact command controls:
  - explicit policy decision required before orchestration dispatch
  - immutable decision audit event required

## 5. Message Integrity and Replay Controls
- Incoming payloads must pass connector authenticity validation.
- Duplicate/replayed payloads are suppressed using idempotency keys and replay windows.
- Idempotency key is required for all externally sourced command/query envelopes.

## 6. Session and Credential Controls
- Connector secrets/tokens must be externally stored and rotated.
- Principal mapping must be revalidated on configured cadence and revocation events.
- Connector outages or validation failures must fail closed for governed actions.

## 7. Observability and Incident Handling
- Required telemetry:
  - authentication failures
  - mapping lookup failures
  - policy denies by channel and reason
  - replay rejections
- Critical security anomalies route to administrator + ceo and owner per escalation policy.

## 8. Normative Rule Bindings
- `IAM-001`: actions require authenticated and attributable principal.
- `OIM-001`: owner-issued commands require policy authorization before execution.
- `OIM-002`: critical interaction events require immutable audit records.
- `OIM-003`: owner channel access must respect role and scope constraints.
- `OIM-004`: alert severity and routing follow constitutional policies.

## 9. Conformance Tests
- Unknown or revoked Discord identities are denied.
- Replay of same external message does not duplicate side effects.
- Out-of-scope Discord channel actions are denied before orchestration.
- Critical Discord interaction events include required audit and policy metadata.
