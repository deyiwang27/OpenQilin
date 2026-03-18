"""M13-WP6 — Sandbox Enforcement Scaffolding.

Unit tests for:
- enforcement.py is no longer an empty placeholder.
- SandboxProfileEnforcer.bind() returns BoundProfile for known profiles.
- SandboxProfileEnforcer.bind() raises SandboxProfileNotFoundError for unknown profiles (fail-closed).
- BoundProfile.as_popen_kwargs() returns the preexec_fn hook on Linux, {} on non-Linux.
- enforce_sandbox_profile obligation handler calls SandboxProfileEnforcer.bind().
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from openqilin.execution_sandbox.profiles.enforcement import (
    BoundProfile,
    SandboxProfileEnforcer,
    SandboxProfileNotFoundError,
)


# ---------------------------------------------------------------------------
# SandboxProfileEnforcer
# ---------------------------------------------------------------------------


class TestSandboxProfileEnforcer:
    def test_bind_default_profile_succeeds(self) -> None:
        enforcer = SandboxProfileEnforcer()
        bound = enforcer.bind(dispatch_target="secretary", profile_name="default")
        assert isinstance(bound, BoundProfile)
        assert bound.dispatch_target == "secretary"
        assert bound.profile_name == "default"
        assert "syscalls" in bound.profile

    def test_bind_unknown_profile_raises_fail_closed(self, tmp_path: Path) -> None:
        """Unknown profile name → SandboxProfileNotFoundError (fail-closed)."""
        enforcer = SandboxProfileEnforcer(profile_dir=tmp_path)
        with pytest.raises(SandboxProfileNotFoundError) as exc_info:
            enforcer.bind(dispatch_target="secretary", profile_name="nonexistent")
        assert "nonexistent" in str(exc_info.value)
        assert exc_info.value.dispatch_target == "secretary"
        assert exc_info.value.profile_name == "nonexistent"

    def test_bind_uses_default_profile_name_by_default(self) -> None:
        enforcer = SandboxProfileEnforcer()
        bound = enforcer.bind(dispatch_target="project_manager")
        assert bound.profile_name == "default"

    def test_bind_for_all_known_agent_targets(self) -> None:
        """All agent roles should be bindable to the default profile."""
        enforcer = SandboxProfileEnforcer()
        for target in ("secretary", "project_manager", "domain_leader", "cso", "ceo", "cwo"):
            bound = enforcer.bind(dispatch_target=target)
            assert bound.dispatch_target == target

    def test_default_profile_json_has_syscalls(self) -> None:
        enforcer = SandboxProfileEnforcer()
        bound = enforcer.bind(dispatch_target="sandbox")
        assert isinstance(bound.profile.get("syscalls"), list)
        assert len(bound.profile["syscalls"]) > 0

    def test_default_profile_default_action_is_deny(self) -> None:
        """defaultAction must be SCMP_ACT_ERRNO (deny unknown syscalls)."""
        enforcer = SandboxProfileEnforcer()
        bound = enforcer.bind(dispatch_target="sandbox")
        assert bound.profile.get("defaultAction") == "SCMP_ACT_ERRNO"


# ---------------------------------------------------------------------------
# BoundProfile.as_popen_kwargs
# ---------------------------------------------------------------------------


class TestBoundProfileAsPopenKwargs:
    def _make_bound(self) -> BoundProfile:
        enforcer = SandboxProfileEnforcer()
        return enforcer.bind(dispatch_target="specialist")

    def test_non_linux_returns_empty_kwargs(self) -> None:
        """On non-Linux platforms, popen_kwargs should be empty (no seccomp)."""
        bound = self._make_bound()
        with patch("platform.system", return_value="Darwin"):
            kwargs = bound.as_popen_kwargs()
        assert kwargs == {}

    def test_linux_returns_preexec_fn(self) -> None:
        """On Linux, popen_kwargs should include preexec_fn."""
        bound = self._make_bound()
        with patch("platform.system", return_value="Linux"):
            kwargs = bound.as_popen_kwargs()
        assert "preexec_fn" in kwargs
        assert callable(kwargs["preexec_fn"])

    def test_linux_preexec_fn_calls_apply_seccomp(self) -> None:
        """The preexec_fn should call _apply_seccomp_filter."""
        bound = self._make_bound()
        called_with = {}

        def mock_apply(profile: dict) -> None:
            called_with["profile"] = profile

        with patch("platform.system", return_value="Linux"):
            with patch(
                "openqilin.execution_sandbox.profiles.enforcement._apply_seccomp_filter",
                side_effect=mock_apply,
            ):
                kwargs = bound.as_popen_kwargs()
                kwargs["preexec_fn"]()

        assert "profile" in called_with
        assert "syscalls" in called_with["profile"]


# ---------------------------------------------------------------------------
# enforce_sandbox_profile obligation handler
# ---------------------------------------------------------------------------


class TestEnforceSandboxProfileObligationHandler:
    def _make_context(self, target: str = "secretary"):
        from unittest.mock import MagicMock
        from openqilin.policy_runtime_integration.obligations import ObligationContext

        return ObligationContext(
            trace_id="trace-1",
            task_id="t-1",
            request_id="req-1",
            principal_id="u-1",
            principal_role="owner",
            action="EXECUTE",
            target=target,
            project_id=None,
            policy_version="v2",
            policy_hash="test-hash",
            rule_ids=("SAF-001",),
            audit_writer=MagicMock(),
            budget_reservation_service=MagicMock(),
            runtime_state_repo=MagicMock(),
            task_record=MagicMock(),
        )

    def test_known_target_satisfies_obligation(self) -> None:
        from openqilin.policy_runtime_integration.obligations import (
            _handle_enforce_sandbox_profile,
        )

        context = self._make_context(target="secretary")
        outcome = _handle_enforce_sandbox_profile(context)
        assert outcome.satisfied is True
        assert outcome.obligation == "enforce_sandbox_profile"

    def test_unknown_profile_returns_unsatisfied_non_blocking(self, tmp_path: Path) -> None:
        """Unknown profile → obligation not satisfied, blocking=False (non-fatal in M13)."""
        from openqilin.policy_runtime_integration.obligations import (
            _handle_enforce_sandbox_profile,
        )

        context = self._make_context(target="unknown_agent")
        # Patch SandboxProfileEnforcer in the enforcement module to use empty tmp_path
        with patch(
            "openqilin.execution_sandbox.profiles.enforcement.SandboxProfileEnforcer.__init__",
            lambda self, profile_dir=None: setattr(self, "_profile_dir", tmp_path),
        ):
            outcome = _handle_enforce_sandbox_profile(context)

        assert outcome.satisfied is False
        assert outcome.blocking is False

    def test_enforcement_is_not_blocking_in_m13(self) -> None:
        """M13 enforcement is non-blocking (hook only); blocking=False always."""
        from openqilin.policy_runtime_integration.obligations import (
            _handle_enforce_sandbox_profile,
        )

        context = self._make_context(target="ceo")
        outcome = _handle_enforce_sandbox_profile(context)
        assert outcome.blocking is False
