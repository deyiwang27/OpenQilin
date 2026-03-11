"""Deterministic retry scheduling policy for communication delivery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RetryScheduleDecision:
    """Retry scheduling decision for one failed delivery attempt."""

    retry: bool
    next_attempt: int
    backoff_seconds: int
    reason_code: str
    message: str


class RetryScheduler(Protocol):
    """Retry scheduler protocol."""

    def schedule_next(
        self,
        *,
        attempt: int,
        error_code: str,
        retryable: bool,
    ) -> RetryScheduleDecision:
        """Resolve deterministic retry decision for failed delivery attempt."""


class DeterministicRetryScheduler:
    """Deterministic retry scheduler with fixed exponential backoff policy."""

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        base_backoff_seconds: int = 2,
        max_backoff_seconds: int = 30,
    ) -> None:
        self._max_attempts = max_attempts
        self._base_backoff_seconds = base_backoff_seconds
        self._max_backoff_seconds = max_backoff_seconds

    def schedule_next(
        self,
        *,
        attempt: int,
        error_code: str,
        retryable: bool,
    ) -> RetryScheduleDecision:
        """Schedule deterministic retry/backoff from current attempt outcome."""

        if not retryable:
            return RetryScheduleDecision(
                retry=False,
                next_attempt=attempt,
                backoff_seconds=0,
                reason_code="communication_retry_not_allowed",
                message=f"retry disabled for non-retryable error: {error_code}",
            )
        if attempt >= self._max_attempts:
            return RetryScheduleDecision(
                retry=False,
                next_attempt=attempt,
                backoff_seconds=0,
                reason_code="communication_retry_exhausted",
                message=f"retry exhausted after {attempt} attempts",
            )
        next_attempt = attempt + 1
        return RetryScheduleDecision(
            retry=True,
            next_attempt=next_attempt,
            backoff_seconds=self.backoff_seconds_for_attempt(next_attempt),
            reason_code="communication_retry_scheduled",
            message=f"retry scheduled for attempt {next_attempt}",
        )

    def backoff_seconds_for_attempt(self, attempt: int) -> int:
        """Calculate deterministic backoff duration for target attempt."""

        if attempt <= 1:
            return 0
        exponent = attempt - 2
        backoff = self._base_backoff_seconds * (2**exponent)
        return min(backoff, self._max_backoff_seconds)
