"""M12-WP1: OPA Policy Runtime Wiring tests.

Tests for:
- OPAPolicyRuntimeClient: fail-closed on HTTP error, timeout, non-200, empty result
- OPAPolicyRuntimeClient: correct deserialization of OPA response
- PolicyRuntimeClient Protocol: OPAPolicyRuntimeClient and InMemoryPolicyRuntimeClient satisfy it
- InMemoryPolicyRuntimeClient still accessible from testing/ path
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from openqilin.policy_runtime_integration.client import (
    OPAPolicyRuntimeClient,
    PolicyRuntimeClient,
)
from openqilin.policy_runtime_integration.models import PolicyEvaluationInput
from openqilin.policy_runtime_integration.testing.in_memory_client import (
    InMemoryPolicyRuntimeClient,
)


def _make_input(**kwargs: object) -> PolicyEvaluationInput:
    defaults: dict[str, object] = {
        "task_id": "task-001",
        "request_id": "req-001",
        "trace_id": "trace-001",
        "principal_id": "owner_001",
        "principal_role": "owner",
        "trust_domain": "internal",
        "connector": "discord",
        "action": "msg_notify",
        "target": "ceo",
        "recipient_types": ("ceo",),
        "recipient_ids": ("ceo_001",),
        "args": (),
        "project_id": None,
    }
    defaults.update(kwargs)
    return PolicyEvaluationInput(**defaults)  # type: ignore[arg-type]


class TestOPAClientFailClosed:
    """OPAPolicyRuntimeClient must fail-closed on all error conditions."""

    def test_transport_error_returns_deny_pol003(self) -> None:
        """Network failure → deny with POL-003."""
        import httpx

        client = OPAPolicyRuntimeClient(opa_url="http://unreachable-opa:8181")
        with patch.object(client._http, "post", side_effect=httpx.ConnectError("refused")):
            result = client.evaluate(_make_input())
        assert result.decision == "deny"
        assert "POL-003" in result.rule_ids

    def test_timeout_returns_deny_pol003(self) -> None:
        """Timeout → deny with POL-003."""
        import httpx

        client = OPAPolicyRuntimeClient(opa_url="http://opa:8181")
        with patch.object(client._http, "post", side_effect=httpx.TimeoutException("timed out")):
            result = client.evaluate(_make_input())
        assert result.decision == "deny"
        assert "POL-003" in result.rule_ids

    def test_non_200_response_returns_deny_pol003(self) -> None:
        """OPA returns 500 → deny with POL-003."""
        client = OPAPolicyRuntimeClient(opa_url="http://opa:8181")
        mock_response = MagicMock()
        mock_response.status_code = 500
        with patch.object(client._http, "post", return_value=mock_response):
            result = client.evaluate(_make_input())
        assert result.decision == "deny"
        assert "POL-003" in result.rule_ids

    def test_empty_result_returns_deny_pol003(self) -> None:
        """OPA returns 200 with null result → deny with POL-003."""
        client = OPAPolicyRuntimeClient(opa_url="http://opa:8181")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": None}
        with patch.object(client._http, "post", return_value=mock_response):
            result = client.evaluate(_make_input())
        assert result.decision == "deny"
        assert "POL-003" in result.rule_ids

    def test_malformed_json_returns_deny_pol003(self) -> None:
        """OPA returns unparseble response → deny with POL-003."""
        client = OPAPolicyRuntimeClient(opa_url="http://opa:8181")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("bad json")
        with patch.object(client._http, "post", return_value=mock_response):
            result = client.evaluate(_make_input())
        assert result.decision == "deny"
        assert "POL-003" in result.rule_ids


class TestOPAClientDeserialization:
    """OPAPolicyRuntimeClient correctly maps OPA response to PolicyEvaluationResult."""

    def _opa_response(self, decision_payload: dict) -> MagicMock:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": decision_payload}
        return mock_response

    def test_allow_decision_deserialized(self) -> None:
        client = OPAPolicyRuntimeClient(opa_url="http://opa:8181")
        opa_payload = {
            "decision": "allow",
            "reason_code": "policy_allowed",
            "reason_message": "allowed",
            "policy_version": "v2",
            "policy_hash": "abc",
            "rule_ids": ["AUTH-002"],
            "obligations": ["emit_audit_event"],
        }
        with patch.object(client._http, "post", return_value=self._opa_response(opa_payload)):
            result = client.evaluate(_make_input())
        assert result.decision == "allow"
        assert result.reason_code == "policy_allowed"
        assert "AUTH-002" in result.rule_ids
        assert "emit_audit_event" in result.obligations

    def test_deny_decision_deserialized(self) -> None:
        client = OPAPolicyRuntimeClient(opa_url="http://opa:8181")
        opa_payload = {
            "decision": "deny",
            "reason_code": "unknown_role",
            "reason_message": "role not recognized",
            "policy_version": "v2",
            "policy_hash": "abc",
            "rule_ids": ["POL-004"],
            "obligations": [],
        }
        with patch.object(client._http, "post", return_value=self._opa_response(opa_payload)):
            result = client.evaluate(_make_input(principal_role="unknown_role"))
        assert result.decision == "deny"
        assert result.reason_code == "unknown_role"
        assert "POL-004" in result.rule_ids


class TestProtocolConformance:
    """Both policy client implementations satisfy PolicyRuntimeClient protocol."""

    def test_in_memory_satisfies_protocol(self) -> None:
        client = InMemoryPolicyRuntimeClient()
        assert isinstance(client, PolicyRuntimeClient)

    def test_opa_client_satisfies_protocol(self) -> None:
        client = OPAPolicyRuntimeClient(opa_url="http://opa:8181")
        assert isinstance(client, PolicyRuntimeClient)


class TestInMemoryClientNewPath:
    """InMemoryPolicyRuntimeClient importable from testing/ and behaviour unchanged."""

    def test_allow_for_known_role(self) -> None:
        client = InMemoryPolicyRuntimeClient()
        result = client.evaluate(_make_input(principal_role="owner"))
        assert result.decision == "allow"

    def test_deny_unknown_role(self) -> None:
        client = InMemoryPolicyRuntimeClient()
        result = client.evaluate(_make_input(principal_role="hacker"))
        assert result.decision == "deny"
        assert "POL-004" in result.rule_ids

    def test_deny_owner_to_specialist(self) -> None:
        client = InMemoryPolicyRuntimeClient()
        result = client.evaluate(_make_input(principal_role="owner", target="specialist"))
        assert result.decision == "deny"
        assert "OIM-005" in result.rule_ids

    def test_deny_prefix_action(self) -> None:
        client = InMemoryPolicyRuntimeClient()
        result = client.evaluate(_make_input(action="deny_this"))
        assert result.decision == "deny"

    def test_uncertain_action(self) -> None:
        client = InMemoryPolicyRuntimeClient()
        result = client.evaluate(_make_input(action="policy_uncertain"))
        assert result.decision == "uncertain"


class TestHealthCheck:
    """OPAPolicyRuntimeClient health_check returns False on connection failure."""

    def test_health_check_false_on_connection_error(self) -> None:
        client = OPAPolicyRuntimeClient(opa_url="http://unreachable-opa:8181")
        with patch.object(client._http, "get", side_effect=Exception("refused")):
            assert client.health_check() is False

    def test_health_check_true_on_200(self) -> None:
        client = OPAPolicyRuntimeClient(opa_url="http://opa:8181")
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch.object(client._http, "get", return_value=mock_response):
            assert client.health_check() is True
