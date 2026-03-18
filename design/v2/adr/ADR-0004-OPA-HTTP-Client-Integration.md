# ADR-0004 — OPA HTTP Client Integration

**Date:** 2026-03-15
**Status:** Approved
**Author:** Claude (Architect)
**Ratified by:** Owner — approved retroactively on 2026-03-17 (M12 merge)
**Supersedes:** —
**Superseded by:** —

---

## Context

OpenQilin's constitution requires all task dispatch to be gated by a policy decision point. In M11 and earlier milestones, `InMemoryPolicyRuntimeClient` acted as a stub that returned `allow` unconditionally for all requests. This gave no real governance enforcement and violated the constitutional requirement that policy decisions be evaluated against the authority matrix and obligation policy.

M12 (Infrastructure Wiring) required wiring a real OPA instance as the decision point. The key design question was: **how should the runtime client connect to OPA, and what happens when OPA is unavailable?**

Relevant constraints from the constitution and spec:
- `spec/constitution/PolicyEngineContract.md`: all task dispatch must receive a policy decision before proceeding.
- `CLAUDE.md` governance constraint: fail-closed default — every new code path defaults to deny on unknown or error state.
- `constitution/core/PolicyRules.yaml`: 12 rules derived from the authority matrix and obligation policy.

---

## Decision

Replace `InMemoryPolicyRuntimeClient` with `OPAPolicyRuntimeClient`: a synchronous httpx-based HTTP client that calls OPA's REST API at `POST /v1/data/openqilin/policy/decide`.

**Fail-closed contract:** any error condition (network failure, timeout >150ms, non-200 response, malformed JSON) returns `PolicyDecision(decision="deny", rule_ids=["POL-003"])` — never raises and never returns allow.

**Startup guard:** if `OPENQILIN_OPA_URL` is configured, `startup_validation.verify_opa_bundle_loaded()` runs at startup and raises `RuntimeError` if OPA is unreachable or the bundle version does not match. The process refuses to start rather than run without policy enforcement.

**Rego bundle:** policy rules are co-located with the runtime code at `src/openqilin/policy_runtime_integration/rego/`. OPA loads the bundle via `--bundle` flag. The JSON data files (`authority_matrix.json`, `obligation_policy.json`) are generated from `constitution/core/` YAML at build time.

**Protocol type:** a `PolicyRuntimeClient` Protocol (structural subtyping) satisfies both `OPAPolicyRuntimeClient` and the test-only `InMemoryPolicyRuntimeClient`. All routers and handlers depend on the Protocol, not the concrete class.

---

## Rationale

| Option | Reason accepted / rejected |
|---|---|
| **Chosen: httpx sync HTTP client, fail-closed** | Simple, no external SDK required. Fail-closed is constitutionally required. 150ms budget matches governance SLO. |
| Alternative: OPA Go SDK | Not available in Python; would require a subprocess bridge — unnecessary complexity. |
| Alternative: Embed OPA as a library (go-opa-wasm) | Python WASM support is unstable; bundle hot-reload not supported. |
| Alternative: Keep InMemory with policy rules in Python | Governance-critical logic in Python dicts is not auditable or independently verifiable. OPA Rego is the constitutionally designated policy language. |

---

## Consequences

- **Implementation:** `OPAPolicyRuntimeClient` in `src/openqilin/policy_runtime_integration/client.py`. `InMemoryPolicyRuntimeClient` moved to `testing/in_memory_client.py` (test-only).
- **Tests:** Rego unit tests for all 12 rules; fail-closed behaviour verified when OPA returns 500 or times out; startup guard tested against unreachable OPA.
- **Governance:** `OPENQILIN_OPA_URL` required in production. Absent URL → startup refuses. This is the M12 prerequisite for DL agent activation.
- **Compose:** OPA service added to `compose.yml` with `--bundle` flag and Rego volume mount. All integration tests require the compose stack.

---

## References

- Spec: `spec/constitution/PolicyEngineContract.md`
- Component delta: `design/v2/components/PolicyRuntimeComponentDelta-v2.md`
- Constitution: `constitution/core/PolicyRules.yaml`, `constitution/core/AuthorityMatrix.yaml`
- Milestone design: `design/v2/architecture/M12-InfrastructureWiringAndSecurityModuleDesign-v2.md`
- Implementing commit: `ce4ad8a` — feat(m12-wp1): OPA policy runtime wiring — C-1
- GitHub issue: #81 (M12-WP1)
