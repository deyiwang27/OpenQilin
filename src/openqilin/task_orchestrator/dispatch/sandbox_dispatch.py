"""Sandbox dispatch stub for M1 governed-path handoff."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class SandboxDispatchRequest:
    """Dispatch payload for sandbox stub."""

    task_id: str
    trace_id: str
    command: str
    args: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SandboxDispatchReceipt:
    """Dispatch acceptance/rejection receipt."""

    accepted: bool
    dispatch_id: str | None
    error_code: str | None
    message: str


class SandboxDispatchStub:
    """Deterministic dispatch stub used by M1-WP5."""

    def dispatch(self, payload: SandboxDispatchRequest) -> SandboxDispatchReceipt:
        """Simulate sandbox dispatch acceptance/rejection."""

        if payload.command == "dispatch_timeout":
            return SandboxDispatchReceipt(
                accepted=False,
                dispatch_id=None,
                error_code="execution_dispatch_timeout",
                message="dispatch timed out at sandbox boundary",
            )

        if payload.command == "dispatch_reject":
            return SandboxDispatchReceipt(
                accepted=False,
                dispatch_id=None,
                error_code="execution_dispatch_failed",
                message="sandbox rejected dispatch request",
            )

        return SandboxDispatchReceipt(
            accepted=True,
            dispatch_id=str(uuid4()),
            error_code=None,
            message="sandbox dispatch accepted",
        )
