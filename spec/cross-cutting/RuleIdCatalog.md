# OpenQilin - Rule ID Catalog Specification

## 1. Scope
- Canonical registry for rule IDs used across specs and constitution artifacts.

## 2. Namespace Pattern
- GOV-*, AUTH-*, ESC-*, SAF-*, POL-*, BUD-*, ORCH-*, SAN-*, AUD-*, SCHEMA-*

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| RID-001 | Rule IDs MUST be unique and stable across versions. | critical | Change Control |

## 4. Conformance Tests
- Duplicate rule IDs fail validation.
