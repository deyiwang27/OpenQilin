# OpenQilin - Rule ID Catalog Specification

## 1. Scope
- Defines canonical rule ID namespaces and machine-readable registry behavior.

## 2. Canonical Artifacts
- Registry artifact: `spec/cross-cutting/RuleRegistry.json`
- Coverage artifact: `spec/cross-cutting/ConformanceCoverage.json`
- Maintenance requirement: registry and coverage artifacts must be updated together.
- Validation requirement: path references and rule ID references must be checked before merge.

## 3. Namespace Pattern
- `AUTH-*` authority and role constraints
- `GOV-*` governance invariants
- `ESC-*` escalation behavior
- `SAF-*` safety doctrine
- `POL-*` policy engine behavior
- `BUD-*` budget controls
- `ORCH-*` orchestration controls
- `A2A-*` inter-agent payload contract
- `ACP-*` communication protocol transport contract
- `SAN-*` sandbox controls
- `RT-*` runtime core controls
- `FRM-*` failure/recovery controls
- `MEM-*` memory controls
- `MET-*` metrics/alerts controls
- `AUD-*` audit controls
- `STR-*` storage/retention controls
- `SCHEMA-*` data schema controls
- `TEST-*` conformance/release controls
- `RID-*` rule-catalog controls
- `GLO-*` glossary controls

## 4. Registry Semantics
- Rule IDs are stable identifiers and may appear in multiple files.
- Registry primary record is one entry per rule ID with all known occurrences.
- Any rule ID referenced in `spec/` or `constitution/` MUST exist in `RuleRegistry.json`.

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
