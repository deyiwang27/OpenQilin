"""Cache-backed idempotency store primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

CacheIdempotencyStatus = Literal["in_progress", "completed"]
CacheClaimStatus = Literal["new", "replay", "conflict", "in_progress"]


@dataclass(frozen=True, slots=True)
class CacheIdempotencyRecord:
    """Stored idempotency record scoped by namespace and key."""

    namespace: str
    key: str
    payload_hash: str
    status: CacheIdempotencyStatus
    attempt_count: int
    result: tuple[tuple[str, str], ...] | None
    created_at: datetime
    updated_at: datetime


class IdempotencyCacheStoreError(ValueError):
    """Raised when idempotency snapshot persistence cannot be completed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
