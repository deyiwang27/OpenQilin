"""Redis-backed idempotency cache store replacing InMemoryIdempotencyCacheStore."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Mapping, cast

import redis

from openqilin.data_access.cache.idempotency_store import (
    CacheClaimStatus,
    CacheIdempotencyRecord,
    CacheIdempotencyStatus,
)


class RedisIdempotencyCacheStore:
    """Redis-backed idempotency cache with the same interface as InMemoryIdempotencyCacheStore.

    Key format: ``idempotency:{namespace}:{key}``
    Claim: SET NX EX (atomic insert-if-absent with TTL).
    All records are stored as JSON strings; TTL is refreshed on update.
    """

    def __init__(
        self,
        *,
        client: redis.Redis,  # type: ignore[type-arg]
        ttl_seconds: int = 86400,
    ) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    def claim(
        self,
        *,
        namespace: str,
        key: str,
        payload_hash: str,
    ) -> tuple[CacheClaimStatus, CacheIdempotencyRecord]:
        """Claim key and resolve new/replay/conflict/in-progress semantics.

        Uses SET NX EX for atomic insert-if-absent.  If the key already exists,
        fetches the stored record and compares payload_hash / status.
        """

        redis_key = _redis_key(namespace, key)
        now = datetime.now(tz=UTC)
        new_record = CacheIdempotencyRecord(
            namespace=namespace,
            key=key,
            payload_hash=payload_hash,
            status="in_progress",
            attempt_count=0,
            result=None,
            created_at=now,
            updated_at=now,
        )
        # SET NX EX: only set if not exists, with TTL.
        was_set = self._client.set(
            redis_key,
            _record_to_json(new_record),
            nx=True,
            ex=self._ttl_seconds,
        )
        if was_set:
            return "new", new_record

        # Key already existed — fetch and classify.
        existing = self._get_record(redis_key)
        if existing is None:
            # Rare race: key expired between SET NX failure and GET; treat as new.
            self._client.set(
                redis_key,
                _record_to_json(new_record),
                ex=self._ttl_seconds,
            )
            return "new", new_record

        if existing.payload_hash != payload_hash:
            return "conflict", existing
        if existing.status == "completed":
            return "replay", existing
        return "in_progress", existing

    def increment_attempt(self, *, namespace: str, key: str) -> CacheIdempotencyRecord | None:
        """Increment attempt counter for existing in-progress record."""

        redis_key = _redis_key(namespace, key)
        existing = self._get_record(redis_key)
        if existing is None:
            return None
        updated = CacheIdempotencyRecord(
            namespace=existing.namespace,
            key=existing.key,
            payload_hash=existing.payload_hash,
            status=existing.status,
            attempt_count=existing.attempt_count + 1,
            result=existing.result,
            created_at=existing.created_at,
            updated_at=datetime.now(tz=UTC),
        )
        self._client.set(redis_key, _record_to_json(updated), keepttl=True)
        return updated

    def complete(
        self,
        *,
        namespace: str,
        key: str,
        result: Mapping[str, object],
    ) -> CacheIdempotencyRecord | None:
        """Mark idempotency record completed with immutable result payload."""

        redis_key = _redis_key(namespace, key)
        existing = self._get_record(redis_key)
        if existing is None:
            return None
        updated = CacheIdempotencyRecord(
            namespace=existing.namespace,
            key=existing.key,
            payload_hash=existing.payload_hash,
            status="completed",
            attempt_count=existing.attempt_count,
            result=tuple(sorted((str(k), str(v)) for k, v in result.items())),
            created_at=existing.created_at,
            updated_at=datetime.now(tz=UTC),
        )
        self._client.set(redis_key, _record_to_json(updated), keepttl=True)
        return updated

    def get(self, *, namespace: str, key: str) -> CacheIdempotencyRecord | None:
        """Load one idempotency record."""

        return self._get_record(_redis_key(namespace, key))

    def list_namespace(self, *, namespace: str) -> tuple[CacheIdempotencyRecord, ...]:
        """List all idempotency records for namespace.

        Uses SCAN to iterate without blocking; collects matching keys then
        fetches values via pipeline for efficiency.
        """

        pattern = f"idempotency:{namespace}:*"
        keys: list[str] = []
        cursor = 0
        while True:
            cursor, batch = self._client.scan(cursor=cursor, match=pattern, count=100)
            keys.extend(str(k.decode() if isinstance(k, bytes) else k) for k in batch)
            if cursor == 0:
                break

        if not keys:
            return ()

        pipe = self._client.pipeline(transaction=False)
        for k in keys:
            pipe.get(k)
        raw_values = pipe.execute()

        records: list[CacheIdempotencyRecord] = []
        for raw in raw_values:
            if raw is not None:
                record = _record_from_json(raw)
                if record is not None:
                    records.append(record)
        return tuple(records)

    def _get_record(self, redis_key: str) -> CacheIdempotencyRecord | None:
        raw = self._client.get(redis_key)
        if raw is None:
            return None
        return _record_from_json(raw)


def build_redis_client(redis_url: str) -> redis.Redis:  # type: ignore[type-arg]
    """Build a synchronous Redis client from a URL string."""

    return redis.Redis.from_url(redis_url, decode_responses=False)


def _redis_key(namespace: str, key: str) -> str:
    return f"idempotency:{namespace}:{key}"


def _record_to_json(record: CacheIdempotencyRecord) -> str:
    return json.dumps(
        {
            "namespace": record.namespace,
            "key": record.key,
            "payload_hash": record.payload_hash,
            "status": record.status,
            "attempt_count": record.attempt_count,
            "result": [list(item) for item in (record.result or ())],
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }
    )


def _record_from_json(raw: bytes | str) -> CacheIdempotencyRecord | None:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    result_raw = data.get("result", [])
    parsed_result = tuple(
        (str(item[0]), str(item[1]))
        for item in result_raw
        if isinstance(item, list) and len(item) == 2
    )
    status = str(data.get("status", "in_progress")).strip().lower()
    if status not in ("in_progress", "completed"):
        status = "in_progress"
    return CacheIdempotencyRecord(
        namespace=str(data["namespace"]),
        key=str(data["key"]),
        payload_hash=str(data["payload_hash"]),
        status=cast(CacheIdempotencyStatus, status),
        attempt_count=int(data.get("attempt_count", 0)),
        result=parsed_result or None,
        created_at=datetime.fromisoformat(str(data["created_at"])).astimezone(UTC),
        updated_at=datetime.fromisoformat(str(data["updated_at"])).astimezone(UTC),
    )
