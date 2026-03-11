"""In-memory cache-backed idempotency store primitives."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal, Mapping

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


class InMemoryIdempotencyCacheStore:
    """Deterministic in-memory idempotency cache used by runtime modules."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], CacheIdempotencyRecord] = {}

    def claim(
        self,
        *,
        namespace: str,
        key: str,
        payload_hash: str,
    ) -> tuple[CacheClaimStatus, CacheIdempotencyRecord]:
        """Claim key and resolve new/replay/conflict/in-progress semantics."""

        record_key = (namespace, key)
        existing = self._records.get(record_key)
        if existing is None:
            now = datetime.now(tz=UTC)
            created = CacheIdempotencyRecord(
                namespace=namespace,
                key=key,
                payload_hash=payload_hash,
                status="in_progress",
                attempt_count=0,
                result=None,
                created_at=now,
                updated_at=now,
            )
            self._records[record_key] = created
            return "new", created

        if existing.payload_hash != payload_hash:
            return "conflict", existing
        if existing.status == "completed":
            return "replay", existing
        return "in_progress", existing

    def increment_attempt(self, *, namespace: str, key: str) -> CacheIdempotencyRecord | None:
        """Increment attempt counter for existing in-progress record."""

        current = self._records.get((namespace, key))
        if current is None:
            return None
        updated = replace(
            current,
            attempt_count=current.attempt_count + 1,
            updated_at=datetime.now(tz=UTC),
        )
        self._records[(namespace, key)] = updated
        return updated

    def complete(
        self,
        *,
        namespace: str,
        key: str,
        result: Mapping[str, object],
    ) -> CacheIdempotencyRecord | None:
        """Mark idempotency record completed with immutable result payload."""

        current = self._records.get((namespace, key))
        if current is None:
            return None
        updated = replace(
            current,
            status="completed",
            result=tuple(sorted((str(k), str(v)) for k, v in result.items())),
            updated_at=datetime.now(tz=UTC),
        )
        self._records[(namespace, key)] = updated
        return updated

    def get(self, *, namespace: str, key: str) -> CacheIdempotencyRecord | None:
        """Load one idempotency record."""

        return self._records.get((namespace, key))

    def list_namespace(self, *, namespace: str) -> tuple[CacheIdempotencyRecord, ...]:
        """List all idempotency records for namespace."""

        return tuple(record for (ns, _), record in self._records.items() if ns == namespace)
