"""Communication-delivery idempotency store wrappers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal, Mapping

from openqilin.data_access.cache.idempotency_store import (
    CacheIdempotencyRecord,
)

CommunicationClaimStatus = Literal["new", "replay", "conflict", "in_progress"]


@dataclass(frozen=True, slots=True)
class CommunicationIdempotencyRecord:
    """Communication idempotency state for duplicate-safe delivery execution."""

    key: str
    payload_hash: str
    status: str
    attempt_count: int
    result: tuple[tuple[str, str], ...] | None


class LocalCommunicationIdempotencyStore:
    """Communication idempotency store backed by an in-process cache store."""

    def __init__(
        self,
        namespace: str = "communication_delivery",
    ) -> None:
        self._namespace = namespace
        self._records: dict[str, CacheIdempotencyRecord] = {}

    def build_delivery_key(
        self,
        *,
        connector: str,
        principal_id: str,
        project_id: str | None,
        idempotency_key: str,
        message_id: str,
        external_message_id: str,
    ) -> str:
        """Build deterministic communication delivery idempotency key."""

        project = project_id or "project-unspecified"
        return (
            f"{connector}:{principal_id}:{project}:"
            f"{idempotency_key}:{message_id}:{external_message_id}"
        )

    def fingerprint_payload(self, payload: Mapping[str, object]) -> str:
        """Create deterministic hash for payload-conflict detection."""

        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def claim(
        self,
        *,
        key: str,
        payload_hash: str,
    ) -> tuple[CommunicationClaimStatus, CommunicationIdempotencyRecord]:
        """Claim communication delivery key for new/replay/conflict resolution."""

        store_key = f"{self._namespace}:{key}"
        existing = self._records.get(store_key)
        if existing is None:
            record = CacheIdempotencyRecord(
                namespace=self._namespace,
                key=key,
                payload_hash=payload_hash,
                status="in_progress",
                attempt_count=0,
                result=None,
                created_at=datetime.now(tz=UTC),
                updated_at=datetime.now(tz=UTC),
            )
            self._records[store_key] = record
            return "new", _to_communication_record(record)

        if existing.status == "in_progress":
            return "in_progress", _to_communication_record(existing)

        if existing.payload_hash != payload_hash:
            return "conflict", _to_communication_record(existing)

        return "replay", _to_communication_record(existing)

    def increment_attempt(self, *, key: str) -> CommunicationIdempotencyRecord | None:
        """Increment communication delivery attempt counter."""

        store_key = f"{self._namespace}:{key}"
        existing = self._records.get(store_key)
        if existing is None:
            return None
        updated = replace(
            existing,
            attempt_count=existing.attempt_count + 1,
            updated_at=datetime.now(tz=UTC),
        )
        self._records[store_key] = updated
        return _to_communication_record(updated)

    def complete(
        self,
        *,
        key: str,
        result: Mapping[str, object],
    ) -> CommunicationIdempotencyRecord | None:
        """Store terminal communication delivery result."""

        store_key = f"{self._namespace}:{key}"
        existing = self._records.get(store_key)
        if existing is None:
            return None
        result_tuple: tuple[tuple[str, str], ...] = tuple(
            (str(k), str(v)) for k, v in result.items()
        )
        updated = replace(
            existing,
            status="completed",
            result=result_tuple,
            updated_at=datetime.now(tz=UTC),
        )
        self._records[store_key] = updated
        return _to_communication_record(updated)

    def get(self, *, key: str) -> CommunicationIdempotencyRecord | None:
        """Load one communication idempotency record."""

        store_key = f"{self._namespace}:{key}"
        record = self._records.get(store_key)
        if record is None:
            return None
        return _to_communication_record(record)

    def list_records(self) -> tuple[CommunicationIdempotencyRecord, ...]:
        """List all communication idempotency records."""

        return tuple(_to_communication_record(record) for record in self._records.values())


def _to_communication_record(record: CacheIdempotencyRecord) -> CommunicationIdempotencyRecord:
    return CommunicationIdempotencyRecord(
        key=record.key,
        payload_hash=record.payload_hash,
        status=record.status,
        attempt_count=record.attempt_count,
        result=record.result,
    )


# Backward-compatible alias retained for existing imports.
InMemoryCommunicationIdempotencyStore = LocalCommunicationIdempotencyStore
