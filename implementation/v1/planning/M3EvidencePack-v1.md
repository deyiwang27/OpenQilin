# OpenQilin v1 - M3 Evidence Pack

Date: `2026-03-11`  
Milestone: `M3 Communication Reliability`  
Primary issue: `#13` (`M3: Communication Reliability Kickoff`)

## 1. Scope
- Consolidate M3 communication reliability evidence for `M3-WP5`.
- Map M3 exit checklist criteria to automated tests and validation commands.

## 2. Validation Commands
- `uv run pytest tests/unit tests/component tests/integration tests/contract tests/conformance`
- `uv run ruff check .`
- `uv run mypy .`
- `uv run python ops/scripts/check_spec_integrity.py`
- Latest validation run on `2026-03-11`: `135 passed` (`pytest`), `ruff` pass, `mypy` pass, and spec-integrity check pass.
- Latest remediation batch commit: `c34e3fb`.

## 3. Test Evidence Map
### 3.1 A2A Envelope Validation and ACP Contract Baseline
- `tests/unit/test_m3_wp1_communication_contract.py`
- `tests/contract/test_m3_wp1_owner_command_communication_contract.py`
- `tests/integration/test_m1_wp1_governed_ingress_path.py`

### 3.2 ACP Send/Ack/Nack Delivery Pipeline
- `tests/unit/test_m3_wp2_delivery_pipeline.py`
- `tests/integration/test_m3_wp2_delivery_path.py`

### 3.3 Retry Scheduler and Duplicate-Safe Idempotency
- `tests/unit/test_m3_wp3_retry_idempotency.py`
- `tests/integration/test_m3_wp3_retry_idempotency_path.py`

### 3.4 Dead-Letter Routing and Alert/Audit Emission
- `tests/unit/test_m3_wp4_dead_letter_writer.py`
- `tests/integration/test_m3_wp4_dead_letter_path.py`

### 3.5 Orchestrator Callback Integration and At-Least-Once Guarantees
- `tests/unit/test_m3_wp5_callback_processor.py`
- `tests/integration/test_m3_wp5_callback_path.py`
- `tests/contract/test_m3_wp5_callback_contract.py`
- `tests/conformance/test_m3_wp5_communication_reliability_conformance.py`

## 4. Acceptance Criteria Mapping
1. A2A envelope validation rejects malformed/invalid traffic deterministically with explicit reason codes: covered by M3-WP1 unit/contract/integration tests.
2. ACP send/ack/nack lifecycle is persisted and duplicate-safe under retry/replay conditions: covered by M3-WP2/M3-WP3 unit+integration tests.
3. Retry policy and dead-letter routing produce deterministic, auditable outcomes: covered by M3-WP3 retry tests plus M3-WP4 dead-letter writer/path tests.
4. Orchestrator callback handling preserves at-least-once semantics without duplicate side effects: covered by M3-WP5 callback processor/integration/contract/conformance tests (duplicate callback replay safety assertions).
5. Full quality gates pass for merged M3 scope (`ruff`, `mypy`, `pytest` suites including contract/conformance): covered by validation commands listed above.
6. M3 post-review consistency checks stay enforced in CI: covered by `ops/scripts/check_spec_integrity.py` wired in `.github/workflows/ci.yml`.

## 5. GitHub Issue Evidence Links
- Parent milestone issue: https://github.com/deyiwang27/OpenQilin/issues/13
- Milestone closeout PR: https://github.com/deyiwang27/OpenQilin/pull/19
- `M3-WP1` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/14, https://github.com/deyiwang27/OpenQilin/issues/14#issuecomment-4042568446
- `M3-WP2` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/15, https://github.com/deyiwang27/OpenQilin/issues/15#issuecomment-4042681776
- `M3-WP3` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/16, https://github.com/deyiwang27/OpenQilin/issues/16#issuecomment-4042744335
- `M3-WP4` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/17, https://github.com/deyiwang27/OpenQilin/issues/17#issuecomment-4042798885
- `M3-WP5` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/18, https://github.com/deyiwang27/OpenQilin/issues/18#issuecomment-4042874734
- Parent progress update for WP5: https://github.com/deyiwang27/OpenQilin/issues/13#issuecomment-4042876018
