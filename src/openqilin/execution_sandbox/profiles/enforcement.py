"""Sandbox profile enforcement — SandboxProfileEnforcer.

M13-WP6 delivers the seccomp profile application hook.
Full namespace/process isolation is deferred to a post-MVP-v2 milestone.

Usage (by ObligationDispatcher ``enforce_sandbox_profile`` handler):

    enforcer = SandboxProfileEnforcer()
    bound = enforcer.bind(dispatch_target="secretary", profile_name="default")
    # bound.as_popen_kwargs() returns subprocess.Popen kwargs that apply the profile
    proc = subprocess.Popen(cmd, **bound.as_popen_kwargs())

The seccomp application hook fires in the child process (via ``preexec_fn``) on Linux.
On non-Linux platforms, the hook is a no-op and a warning is logged.
"""

from __future__ import annotations

import json
import logging
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

_PROFILE_DIR = Path(__file__).parent / "seccomp_profiles"
_DEFAULT_PROFILE = "default"


@dataclass(frozen=True, slots=True)
class BoundProfile:
    """A seccomp profile bound to a specific dispatch target.

    ``as_popen_kwargs()`` returns kwargs for ``subprocess.Popen`` that apply
    the seccomp filter in the child process via ``preexec_fn`` (Linux only).
    """

    dispatch_target: str
    profile_name: str
    profile: dict[str, Any]

    def as_popen_kwargs(self) -> dict[str, Any]:
        """Return ``subprocess.Popen`` kwargs that activate the seccomp profile hook.

        On Linux: returns ``{"preexec_fn": <seccomp hook>}``.
        On other platforms: returns ``{}`` (no-op; seccomp is Linux-only).
        """
        if platform.system() != "Linux":
            LOGGER.warning(
                "sandbox.seccomp.platform_skip",
                extra={
                    "dispatch_target": self.dispatch_target,
                    "profile_name": self.profile_name,
                    "platform": platform.system(),
                    "reason": "seccomp is Linux-only; enforcement skipped on this platform",
                },
            )
            return {}

        profile_snapshot = self.profile

        def _preexec_apply_seccomp() -> None:
            _apply_seccomp_filter(profile_snapshot)

        return {"preexec_fn": _preexec_apply_seccomp}


class SandboxProfileEnforcer:
    """Resolves and binds seccomp profiles for sandboxed subprocess execution.

    ``bind(dispatch_target, profile_name)`` loads the named JSON seccomp profile
    and returns a ``BoundProfile`` ready for use with ``subprocess.Popen``.

    Fail-closed: unknown profile names raise ``SandboxProfileNotFoundError``.
    """

    def __init__(self, profile_dir: Path | None = None) -> None:
        self._profile_dir = profile_dir or _PROFILE_DIR

    def bind(self, dispatch_target: str, profile_name: str = _DEFAULT_PROFILE) -> BoundProfile:
        """Resolve the named seccomp profile and bind it to the dispatch target.

        Raises ``SandboxProfileNotFoundError`` if the profile file does not exist.
        """
        profile_path = self._profile_dir / f"{profile_name}.json"
        if not profile_path.exists():
            raise SandboxProfileNotFoundError(
                dispatch_target=dispatch_target,
                profile_name=profile_name,
                profile_path=profile_path,
            )
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        LOGGER.info(
            "sandbox.profile.bound",
            extra={
                "dispatch_target": dispatch_target,
                "profile_name": profile_name,
            },
        )
        return BoundProfile(
            dispatch_target=dispatch_target,
            profile_name=profile_name,
            profile=profile,
        )


class SandboxProfileNotFoundError(FileNotFoundError):
    """Raised when the requested seccomp profile file cannot be found.

    Fail-closed: callers must handle this explicitly.
    """

    def __init__(self, *, dispatch_target: str, profile_name: str, profile_path: Path) -> None:
        super().__init__(
            f"Seccomp profile '{profile_name}' not found for dispatch target "
            f"'{dispatch_target}' (expected: {profile_path})"
        )
        self.dispatch_target = dispatch_target
        self.profile_name = profile_name
        self.profile_path = profile_path


# ---------------------------------------------------------------------------
# Linux seccomp application hook (M13 scope: hook; full BPF filter in post-MVP-v2)
# ---------------------------------------------------------------------------


def _apply_seccomp_filter(profile: dict[str, Any]) -> None:
    """Apply seccomp filter in the child process (Linux only).

    M13 scope: installs the preexec hook entry point.
    Full BPF filter compilation from the OCI profile JSON is deferred to
    a post-MVP-v2 milestone. This hook logs the application and returns.

    Post-MVP-v2: replace this stub with libseccomp-based BPF compilation and
    ``prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ...)`` application.
    """
    # Full namespace/process isolation deferred to post-MVP-v2.
    # M13 establishes the hook entry point and profile binding only.
    sys.stderr.write(
        f"[sandbox] seccomp hook activated (profile='{profile.get('_comment', 'default')}'). "
        "Full BPF filter enforcement deferred to post-MVP-v2.\n"
    )
