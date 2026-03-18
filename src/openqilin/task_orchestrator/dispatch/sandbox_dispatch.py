"""Sandbox execution adapter boundary for governed dispatch handoff."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class SandboxDispatchRequest:
    """Dispatch payload for sandbox adapter."""

    task_id: str
    trace_id: str
    command: str
    args: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SandboxDispatchReceipt:
    """Sandbox adapter acceptance/rejection receipt."""

    accepted: bool
    dispatch_id: str | None
    error_code: str | None
    message: str


class SandboxExecutionAdapter(Protocol):
    """Sandbox execution adapter contract for task dispatch handoff."""

    def dispatch(self, payload: SandboxDispatchRequest) -> SandboxDispatchReceipt:
        """Dispatch an admitted task through sandbox adapter boundary."""


class LocalSandboxExecutionAdapter:
    """Deterministic local sandbox adapter for local and test execution."""

    def dispatch(self, payload: SandboxDispatchRequest) -> SandboxDispatchReceipt:
        """Simulate sandbox adapter acceptance/rejection outcomes."""

        if payload.command == "dispatch_timeout":
            return SandboxDispatchReceipt(
                accepted=False,
                dispatch_id=None,
                error_code="execution_dispatch_timeout",
                message="dispatch timed out at sandbox adapter boundary",
            )

        if payload.command == "dispatch_reject":
            return SandboxDispatchReceipt(
                accepted=False,
                dispatch_id=None,
                error_code="execution_dispatch_failed",
                message="sandbox adapter rejected dispatch request",
            )

        return SandboxDispatchReceipt(
            accepted=True,
            dispatch_id=str(uuid4()),
            error_code=None,
            message="sandbox adapter accepted dispatch request",
        )


class SandboxDispatchStub(LocalSandboxExecutionAdapter):
    """Backward-compatible alias retained for existing tests/imports."""


# Backward-compatible alias retained for existing imports.
InMemorySandboxExecutionAdapter = LocalSandboxExecutionAdapter
