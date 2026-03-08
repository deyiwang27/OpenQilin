# OpenQilin - Data Model and Schemas Specification

## 1. Scope
- Defines canonical entities and event envelope schemas.

## 2. Canonical Event Envelope
```json
{
  "schema_version": "string",
  "event_id": "uuid",
  "event_type": "string",
  "timestamp": "RFC3339",
  "trace_id": "uuid",
  "policy_version": "string",
  "policy_hash": "string",
  "rule_ids": ["string"],
  "payload": {}
}
```

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| SCHEMA-001 | Every schema MUST carry explicit schema_version. | critical | Runtime |

## 4. Conformance Tests
- Events missing schema_version are rejected.
