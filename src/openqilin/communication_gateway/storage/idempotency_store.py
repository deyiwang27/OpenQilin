"""Communication-delivery idempotency store wrappers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal, Mapping

from openqilin.data_access.cache.idempotency_store import (
    CacheClaimStatus,
    CacheIdempotencyRecord,
    InMemoryIdempotencyCacheStore,
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


class InMemoryCommunicationIdempotencyStore:
    """Communication idempotency store backed by in-memory cache store."""

    def __init__(
        self,
        cache_store: InMemoryIdempotencyCacheStore | None = None,
        namespace: str = "communication_delivery",
    ) -> None:
        self._cache_store = cache_store or InMemoryIdempotencyCacheStore()
        self._namespace = namespace

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

        status, record = self._cache_store.claim(
            namespace=self._namespace,
            key=key,
            payload_hash=payload_hash,
        )
        return _normalize_claim_status(status), _to_communication_record(record)

    def increment_attempt(self, *, key: str) -> CommunicationIdempotencyRecord | None:
        """Increment communication delivery attempt counter."""

        record = self._cache_store.increment_attempt(namespace=self._namespace, key=key)
        if record is None:
            return None
        return _to_communication_record(record)

    def complete(
        self,
        *,
        key: str,
        result: Mapping[str, object],
    ) -> CommunicationIdempotencyRecord | None:
        """Store terminal communication delivery result."""

        record = self._cache_store.complete(
            namespace=self._namespace,
            key=key,
            result=result,
        )
        if record is None:
            return None
        return _to_communication_record(record)

    def get(self, *, key: str) -> CommunicationIdempotencyRecord | None:
        """Load one communication idempotency record."""

        record = self._cache_store.get(namespace=self._namespace, key=key)
        if record is None:
            return None
        return _to_communication_record(record)

    def list_records(self) -> tuple[CommunicationIdempotencyRecord, ...]:
        """List all communication idempotency records."""

        return tuple(
            _to_communication_record(record)
            for record in self._cache_store.list_namespace(namespace=self._namespace)
        )


def _normalize_claim_status(value: CacheClaimStatus) -> CommunicationClaimStatus:
    if value in {"new", "replay", "conflict", "in_progress"}:
        return value
    return "in_progress"


def _to_communication_record(record: CacheIdempotencyRecord) -> CommunicationIdempotencyRecord:
    return CommunicationIdempotencyRecord(
        key=record.key,
        payload_hash=record.payload_hash,
        status=record.status,
        attempt_count=record.attempt_count,
        result=record.result,
    )
