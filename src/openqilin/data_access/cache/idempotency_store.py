"""In-memory cache-backed idempotency store primitives."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Mapping, cast

from openqilin.shared_kernel.config import RuntimeSettings

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


class InMemoryIdempotencyCacheStore:
    """Deterministic in-memory idempotency cache used by runtime modules."""

    def __init__(self, *, snapshot_path: Path | None = None) -> None:
        self._records: dict[tuple[str, str], CacheIdempotencyRecord] = {}
        self._snapshot_path = snapshot_path
        if self._snapshot_path is not None:
            self._load_snapshot()

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
            self._flush_snapshot()
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
        self._flush_snapshot()
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
        self._flush_snapshot()
        return updated

    def get(self, *, namespace: str, key: str) -> CacheIdempotencyRecord | None:
        """Load one idempotency record."""

        return self._records.get((namespace, key))

    def list_namespace(self, *, namespace: str) -> tuple[CacheIdempotencyRecord, ...]:
        """List all idempotency records for namespace."""

        return tuple(record for (ns, _), record in self._records.items() if ns == namespace)

    def _load_snapshot(self) -> None:
        path = self._resolved_snapshot_path()
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise IdempotencyCacheStoreError(
                code="idempotency_snapshot_load_failed",
                message=f"failed to load idempotency snapshot: {path}",
            ) from error
        records = payload.get("records", [])
        if not isinstance(records, list):
            raise IdempotencyCacheStoreError(
                code="idempotency_snapshot_invalid",
                message="idempotency snapshot payload must include list records",
            )
        for raw in records:
            record = _record_from_dict(raw)
            self._records[(record.namespace, record.key)] = record

    def _flush_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        path = self._resolved_snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "records": [_record_to_dict(record) for record in self._records.values()],
        }
        try:
            path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        except OSError as error:
            raise IdempotencyCacheStoreError(
                code="idempotency_snapshot_write_failed",
                message=f"failed to write idempotency snapshot: {path}",
            ) from error

    def _resolved_snapshot_path(self) -> Path:
        if self._snapshot_path is not None:
            return self._snapshot_path
        return RuntimeSettings().idempotency_snapshot_path


def _record_to_dict(record: CacheIdempotencyRecord) -> dict[str, object]:
    return {
        "namespace": record.namespace,
        "key": record.key,
        "payload_hash": record.payload_hash,
        "status": record.status,
        "attempt_count": record.attempt_count,
        "result": [list(item) for item in (record.result or ())],
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def _record_from_dict(raw: object) -> CacheIdempotencyRecord:
    if not isinstance(raw, dict):
        raise IdempotencyCacheStoreError(
            code="idempotency_snapshot_invalid_record",
            message="idempotency snapshot record must be an object",
        )
    result = raw.get("result", [])
    parsed_result = tuple(
        (str(item[0]), str(item[1])) for item in result if isinstance(item, list) and len(item) == 2
    )
    return CacheIdempotencyRecord(
        namespace=str(raw["namespace"]),
        key=str(raw["key"]),
        payload_hash=str(raw["payload_hash"]),
        status=_parse_cache_status(str(raw["status"])),
        attempt_count=int(raw["attempt_count"]),
        result=parsed_result or None,
        created_at=datetime.fromisoformat(str(raw["created_at"])).astimezone(UTC),
        updated_at=datetime.fromisoformat(str(raw["updated_at"])).astimezone(UTC),
    )


def _parse_cache_status(value: str) -> CacheIdempotencyStatus:
    normalized = value.strip().lower()
    if normalized in {"in_progress", "completed"}:
        return cast(CacheIdempotencyStatus, normalized)
    raise IdempotencyCacheStoreError(
        code="idempotency_snapshot_invalid_status",
        message=f"invalid idempotency status in snapshot: {value}",
    )
