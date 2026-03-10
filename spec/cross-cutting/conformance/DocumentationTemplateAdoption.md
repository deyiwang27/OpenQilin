# OpenQilin - Documentation Template Adoption Standard

## 1. Scope
- Defines mandatory template usage for new specifications and constitutional policies.
- Standardizes documentation structure for maintainability and machine-readability.

## 2. Mandatory Templates
- Implementation contracts:
  - `spec/templates/ImplementationContractTemplate.md`
- Role contracts:
  - `spec/templates/RoleContractTemplate.md`
- Domain constitutional policies:
  - `constitution/templates/DomainPolicyTemplate.yaml`

## 3. Adoption Rules
- New role-specific specifications must start from role contract template.
- New domain policy YAML files must start from domain policy template.
- New implementation-facing specs should follow implementation contract template sections unless an approved exception is documented.
- Template-derived files must replace all placeholder tokens before merge.

## 4. Exception Handling
- Exceptions are allowed only when template structure is not applicable.
- Exception record must include:
  - reason
  - approved_by_role
  - affected file paths
  - compensating structure notes

## 5. Migration Guidance
- Existing legacy docs are not required to be rewritten immediately.
- Any major revision to an existing doc should align it with the relevant template where practical.
- Role-contract migration priority:
  1. support and governance roles
  2. executive roles
  3. operations and specialist roles

## 6. Quality Gate Hooks
- Pre-merge review verifies:
  - template alignment for new docs
  - no unresolved placeholders
  - required sections present for contract-bearing docs

## 7. Normative Rule Bindings
- `DOC-001`: implementation specs should retain required structural sections.
- `TEST-002`: integrity checks pass before merge/release.
- `RID-004`: unresolved references fail validation.

## 8. Conformance Tests
- New role spec without role-contract structure fails review.
- New policy YAML not based on domain policy template fails review.
- Placeholder tokens in template-derived docs block merge.
