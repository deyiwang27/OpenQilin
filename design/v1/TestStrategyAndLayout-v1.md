# OpenQilin v1 - Test Strategy and Layout

## 1. Scope
- Define the automated testing layers required for v1 implementation.
- Define test package layout, local execution expectations, and minimum quality bar before merge.

## 2. Test Layers
### 2.1 Unit Tests
Purpose:
- validate isolated module behavior with no external infrastructure dependency

Required for:
- request/response normalization
- state transition helpers
- policy/budget wrappers
- retry/backoff logic
- config validation

### 2.2 Component Tests
Purpose:
- validate one runtime component with fakes/stubs for its collaborators

Examples:
- control plane handler behavior
- orchestrator admission flow with stubbed policy/budget
- llm gateway routing-profile resolution

### 2.3 Contract Tests
Purpose:
- validate implementation request/response/error envelopes against Define-stage contracts

Required targets:
- control-plane ingress
- policy request/response mapping
- llm gateway request/response
- A2A/ACP envelopes

### 2.4 Integration Tests
Purpose:
- validate multi-component flows with real infrastructure dependencies

Minimum v1 flow:
- API ingress -> orchestrator -> policy -> budget -> dispatch stub -> audit/trace persistence

### 2.5 Conformance and Recovery Smoke Tests
Purpose:
- validate governance-core and recovery gates required by `spec/`

Required focus:
- fail-closed behavior
- retry/idempotency safety
- state-machine integrity
- restart artifact validation

## 3. Tests Layout
```text
tests/
  unit/
  component/
  contract/
  integration/
  conformance/
```

## 4. Minimum Quality Bar
Before merge:
- changed modules require unit tests
- contract-touching changes require contract tests
- governance-core path changes require at least one integration or conformance test
- critical bug fixes require regression coverage

## 5. Local Execution Expectations
Fast local loop:
```bash
uv run pytest tests/unit tests/component
```

Contract and integration loop:
```bash
uv run pytest tests/contract tests/integration
```

Conformance smoke loop:
```bash
uv run pytest tests/conformance
```

## 6. Test Data and Fixtures
- fixture data should reflect canonical roles, policy metadata, and task states
- test fixtures should create deterministic IDs and timestamps where possible
- infrastructure-backed tests should use isolated databases/containers

## 7. CI Expectations
- unit + component tests run on every PR
- contract tests run on every PR
- integration and conformance smoke tests run on PR or protected-branch policy as selected in CI/CD design

## 8. Related Design Follow-Ups
- CI gates are defined in `CICDAndQualityGateDesign-v1.md`
- repo layout is defined in `RepoStructureAndPackageLayout-v1.md`
- bootstrap infrastructure is defined in `BootstrapAndMigrationWorkflow-v1.md`
