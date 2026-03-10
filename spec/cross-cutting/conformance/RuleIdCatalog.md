# OpenQilin - Rule ID Catalog Specification

## 1. Scope
- Defines canonical rule ID namespaces and machine-readable registry behavior.

## 2. Canonical Artifacts
- Registry artifact: `spec/cross-cutting/conformance/RuleRegistry.json`
- Coverage artifact: `spec/cross-cutting/conformance/ConformanceCoverage.json`
- Maintenance requirement: registry and coverage artifacts must be updated together.
- Validation requirement: path references and rule ID references must be checked before merge.

## 3. Namespace Pattern
- Canonical rule ID format: `^[A-Z0-9]{2,10}-[0-9]{3}$`
- Only IDs matching the canonical format are treated as governed rule IDs.
- `AUTH-*` authority and role constraints
- `GOV-*` governance invariants
- `ESC-*` escalation behavior
- `SAF-*` safety doctrine
- `POL-*` policy engine behavior
- `BUD-*` budget controls
- `CONS-*` constitution management controls
- `CBM-*` constitution binding controls
- `PVC-*` policy version/change controls
- `ORCH-*` orchestration controls
- `REG-*` agent registry controls
- `TOOL-*` tool registry controls
- `OIM-*` owner interaction controls
- `A2A-*` inter-agent payload contract
- `ACP-*` communication protocol transport contract
- `SAN-*` sandbox controls
- `RT-*` runtime core controls
- `FRM-*` failure/recovery controls
- `MEM-*` memory controls
- `OBS-*` observability architecture controls
- `MET-*` metrics/alerts controls
- `LOG-*` system log controls
- `TRC-*` tracing controls
- `AUD-*` audit controls
- `STR-*` storage/retention controls
- `SCHEMA-*` data schema controls
- `IAM-*` identity and access controls
- `ERR-*` error handling controls
- `DOC-*` documentation/template controls
- `GATE-*` review gate controls
- `TEST-*` conformance/release controls
- `RID-*` rule-catalog controls
- `GLO-*` glossary controls

## 4. Registry Semantics
- Rule IDs are stable identifiers and may appear in multiple files.
- Registry primary record is one entry per rule ID with all known occurrences.
- Any canonical rule ID (matching Section 3 format) referenced in `spec/` or `constitution/` MUST exist in `RuleRegistry.json`.

## 5. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| RID-001 | Rule IDs MUST be unique within the machine-readable registry. | critical | change_control |
| RID-002 | Any rule ID reference in governed artifacts MUST resolve in the registry. | critical | ci_pipeline |
| RID-003 | Registry and coverage artifacts MUST be regenerated on rule updates. | high | ci_pipeline |
| RID-004 | Integrity validation MUST fail on broken path references or unresolved rule IDs. | high | ci_pipeline |

## 6. Conformance Tests
- Duplicate registry IDs fail generation/validation.
- Unknown rule IDs referenced in docs fail integrity check.
- Registry and coverage artifacts stay synchronized.
