"""Policy runtime client — OPA HTTP integration.

Production client: OPAPolicyRuntimeClient (contacts real OPA container).
Test client: InMemoryPolicyRuntimeClient in testing/in_memory_client.py.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import httpx

from openqilin.policy_runtime_integration.models import (
    PolicyEvaluationInput,
    PolicyEvaluationResult,
)

# ---------------------------------------------------------------------------
# Protocol (structural interface used by fail_closed and all routers)
# ---------------------------------------------------------------------------


@runtime_checkable
class PolicyRuntimeClient(Protocol):
    """Structural protocol for synchronous policy evaluation."""

    def evaluate(self, payload: PolicyEvaluationInput) -> PolicyEvaluationResult:
        """Return a policy decision for the given evaluation input."""
        ...


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class PolicyRuntimeClientError(RuntimeError):
    """Raised when policy runtime call cannot be completed."""


# ---------------------------------------------------------------------------
# OPA HTTP client (production)
# ---------------------------------------------------------------------------

_OPA_DECIDE_PATH = "/v1/data/openqilin/policy/decide"
_OPA_HEALTH_PATH = "/health"
_OPA_VERSION_PATH = "/v1/data/openqilin/policy/version"

_POLICY_VERSION_FALLBACK = "unknown"
_TIMEOUT_SECONDS = 0.15  # 150 ms budget per ADR-0004


class OPAPolicyRuntimeClient:
    """Synchronous OPA HTTP policy client with fail-closed semantics.

    All network or protocol errors result in a deny decision with POL-003
    (fail-closed per PolicyRules.yaml).  The caller is never exposed to raw
    HTTP exceptions.
    """

    def __init__(self, opa_url: str) -> None:
        self._opa_url = opa_url.rstrip("/")
        self._http = httpx.Client(timeout=_TIMEOUT_SECONDS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, payload: PolicyEvaluationInput) -> PolicyEvaluationResult:
        """POST evaluation input to OPA and return the policy decision.

        Fail-closed: any network error, timeout, or non-200 response → deny POL-003.
        """
        return self._query_opa(payload)

    def health_check(self) -> bool:
        """Return True when OPA /health endpoint returns 200."""
        try:
            response = self._http.get(f"{self._opa_url}{_OPA_HEALTH_PATH}")
            return response.status_code == 200
        except Exception:
            return False

    def get_active_policy_version(self) -> str:
        """Return the active bundle policy_version string, or 'unknown' on error."""
        try:
            response = self._http.get(f"{self._opa_url}{_OPA_VERSION_PATH}")
            if response.status_code == 200:
                data = response.json()
                return str(data.get("result", _POLICY_VERSION_FALLBACK))
        except Exception:
            pass
        return _POLICY_VERSION_FALLBACK

    def close(self) -> None:
        """Release underlying HTTP connection pool."""
        self._http.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _query_opa(self, payload: PolicyEvaluationInput) -> PolicyEvaluationResult:
        opa_input = _serialize_input(payload)
        try:
            response = self._http.post(
                f"{self._opa_url}{_OPA_DECIDE_PATH}",
                json={"input": opa_input},
                headers={"Content-Type": "application/json"},
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            return _fail_closed_result(f"OPA transport error: {exc}")
        except Exception as exc:
            return _fail_closed_result(f"OPA call failed: {exc}")

        if response.status_code != 200:
            return _fail_closed_result(f"OPA returned HTTP {response.status_code}")

        try:
            body = response.json()
            result_raw = body.get("result")
        except Exception as exc:
            return _fail_closed_result(f"OPA response parse error: {exc}")

        if result_raw is None:
            # OPA returns empty result when no rule matches — treat as deny/fail-closed
            return _fail_closed_result("OPA returned empty result (no matching rule)")

        return _deserialize_result(result_raw)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_input(payload: PolicyEvaluationInput) -> dict[str, Any]:
    return {
        "task_id": payload.task_id,
        "request_id": payload.request_id,
        "trace_id": payload.trace_id,
        "principal_id": payload.principal_id,
        "principal_role": payload.principal_role,
        "trust_domain": payload.trust_domain,
        "connector": payload.connector,
        "action": payload.action,
        "target": payload.target,
        "recipient_types": list(payload.recipient_types),
        "recipient_ids": list(payload.recipient_ids),
        "args": list(payload.args),
        "project_id": payload.project_id,
    }


def _deserialize_result(raw: dict[str, Any]) -> PolicyEvaluationResult:
    """Convert OPA decide response dict to PolicyEvaluationResult."""
    return PolicyEvaluationResult(
        decision=raw.get("decision", "deny"),
        reason_code=raw.get("reason_code", "opa_result_parse_error"),
        reason_message=raw.get("reason_message", "unexpected OPA response structure"),
        policy_version=raw.get("policy_version", _POLICY_VERSION_FALLBACK),
        policy_hash=raw.get("policy_hash", "unknown"),
        rule_ids=tuple(raw.get("rule_ids", [])),
        obligations=tuple(raw.get("obligations", [])),
    )


def _fail_closed_result(reason: str) -> PolicyEvaluationResult:
    """Return a deny/POL-003 result for any failure mode."""
    return PolicyEvaluationResult(
        decision="deny",
        reason_code="POL-003",
        reason_message=f"policy evaluation failed (fail-closed): {reason}",
        policy_version=_POLICY_VERSION_FALLBACK,
        policy_hash="unknown",
        rule_ids=("POL-003",),
    )
