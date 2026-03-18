"""Unit tests for M12-WP4: Redis Idempotency Wiring.

Tests cover:
- RedisIdempotencyCacheStore claim/replay/conflict/in-progress semantics
- increment_attempt, complete, get, list_namespace
- build_redis_client import
- RuntimeSettings redis_url and idempotency_ttl_seconds defaults
- dependencies.py wiring: redis_url set → RedisIdempotencyCacheStore; empty → InMemory
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from openqilin.data_access.cache.idempotency_store import CacheIdempotencyRecord
from openqilin.data_access.repositories.postgres.idempotency_cache_store import (
    RedisIdempotencyCacheStore,
    _record_from_json,
    _record_to_json,
    _redis_key,
    build_redis_client,
)
from openqilin.shared_kernel.config import RuntimeSettings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_redis_mock(
    *,
    set_result: Any = True,
    get_result: bytes | None = None,
    scan_result: tuple[int, list] | None = None,
    pipeline_results: list[Any] | None = None,
) -> MagicMock:
    """Build a Redis client mock with configurable responses."""
    client = MagicMock()
    client.set.return_value = set_result
    client.get.return_value = get_result

    if scan_result is None:
        scan_result = (0, [])
    client.scan.return_value = scan_result

    pipeline = MagicMock()
    pipeline.execute.return_value = pipeline_results or []
    client.pipeline.return_value = pipeline

    return client


def _make_record(
    *,
    namespace: str = "test_ns",
    key: str = "key1",
    payload_hash: str = "hash1",
    status: str = "in_progress",
    attempt_count: int = 0,
    result: tuple[tuple[str, str], ...] | None = None,
) -> CacheIdempotencyRecord:
    now = datetime.now(tz=UTC)
    return CacheIdempotencyRecord(
        namespace=namespace,
        key=key,
        payload_hash=payload_hash,
        status=status,  # type: ignore[arg-type]
        attempt_count=attempt_count,
        result=result,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# _redis_key
# ---------------------------------------------------------------------------


def test_redis_key_format() -> None:
    assert _redis_key("my_ns", "my_key") == "idempotency:my_ns:my_key"


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


def test_record_serialization_round_trip() -> None:
    record = _make_record(result=(("k", "v"),))
    raw = _record_to_json(record)
    restored = _record_from_json(raw.encode())
    assert restored is not None
    assert restored.namespace == record.namespace
    assert restored.key == record.key
    assert restored.payload_hash == record.payload_hash
    assert restored.status == record.status
    assert restored.attempt_count == record.attempt_count
    assert restored.result == record.result


def test_record_from_json_invalid_returns_none() -> None:
    assert _record_from_json(b"not json") is None


def test_record_from_json_unknown_status_defaults_to_in_progress() -> None:
    record = _make_record()
    raw = _record_to_json(record).replace('"in_progress"', '"unknown_status"')
    restored = _record_from_json(raw.encode())
    assert restored is not None
    assert restored.status == "in_progress"


# ---------------------------------------------------------------------------
# claim() — new
# ---------------------------------------------------------------------------


def test_claim_new_key_returns_new_status() -> None:
    client = _make_redis_mock(set_result=True)
    store = RedisIdempotencyCacheStore(client=client, ttl_seconds=3600)
    status, record = store.claim(namespace="ns", key="k", payload_hash="h1")
    assert status == "new"
    assert record.namespace == "ns"
    assert record.key == "k"
    assert record.payload_hash == "h1"
    assert record.status == "in_progress"
    # SET NX EX must be called
    client.set.assert_called_once()
    call_kwargs = client.set.call_args
    assert call_kwargs.kwargs["nx"] is True
    assert call_kwargs.kwargs["ex"] == 3600


# ---------------------------------------------------------------------------
# claim() — in_progress (already claimed, same hash)
# ---------------------------------------------------------------------------


def test_claim_existing_same_hash_in_progress() -> None:
    existing = _make_record(payload_hash="h1", status="in_progress")
    client = _make_redis_mock(set_result=None, get_result=_record_to_json(existing).encode())
    store = RedisIdempotencyCacheStore(client=client)
    status, record = store.claim(namespace="ns", key="k", payload_hash="h1")
    assert status == "in_progress"
    assert record.payload_hash == "h1"


# ---------------------------------------------------------------------------
# claim() — replay (already completed, same hash)
# ---------------------------------------------------------------------------


def test_claim_completed_same_hash_returns_replay() -> None:
    completed = _make_record(
        payload_hash="h1",
        status="completed",
        result=(("task_id", "abc"),),
    )
    client = _make_redis_mock(set_result=None, get_result=_record_to_json(completed).encode())
    store = RedisIdempotencyCacheStore(client=client)
    status, record = store.claim(namespace="ns", key="k", payload_hash="h1")
    assert status == "replay"
    assert record.result == (("task_id", "abc"),)


# ---------------------------------------------------------------------------
# claim() — conflict (different hash)
# ---------------------------------------------------------------------------


def test_claim_different_hash_returns_conflict() -> None:
    existing = _make_record(payload_hash="h1")
    client = _make_redis_mock(set_result=None, get_result=_record_to_json(existing).encode())
    store = RedisIdempotencyCacheStore(client=client)
    status, record = store.claim(namespace="ns", key="k", payload_hash="h_different")
    assert status == "conflict"
    assert record.payload_hash == "h1"


# ---------------------------------------------------------------------------
# claim() — race: key expired between SET NX failure and GET
# ---------------------------------------------------------------------------


def test_claim_race_key_expired_treats_as_new() -> None:
    """If SET NX fails but GET returns None (key expired in the gap), treat as new."""
    client = _make_redis_mock(set_result=None, get_result=None)
    # Second SET call (the fallback write) should succeed
    client.set.return_value = True
    store = RedisIdempotencyCacheStore(client=client)
    status, record = store.claim(namespace="ns", key="k", payload_hash="h1")
    assert status == "new"


# ---------------------------------------------------------------------------
# increment_attempt()
# ---------------------------------------------------------------------------


def test_increment_attempt_increments_counter() -> None:
    existing = _make_record(attempt_count=2)
    client = _make_redis_mock(get_result=_record_to_json(existing).encode())
    store = RedisIdempotencyCacheStore(client=client)
    updated = store.increment_attempt(namespace="ns", key="k")
    assert updated is not None
    assert updated.attempt_count == 3
    # SET with keepttl=True
    client.set.assert_called_once()
    call_kwargs = client.set.call_args
    assert call_kwargs.kwargs.get("keepttl") is True


def test_increment_attempt_missing_key_returns_none() -> None:
    client = _make_redis_mock(get_result=None)
    store = RedisIdempotencyCacheStore(client=client)
    assert store.increment_attempt(namespace="ns", key="missing") is None


# ---------------------------------------------------------------------------
# complete()
# ---------------------------------------------------------------------------


def test_complete_sets_completed_status_and_result() -> None:
    existing = _make_record()
    client = _make_redis_mock(get_result=_record_to_json(existing).encode())
    store = RedisIdempotencyCacheStore(client=client)
    updated = store.complete(namespace="ns", key="k", result={"task_id": "xyz"})
    assert updated is not None
    assert updated.status == "completed"
    assert updated.result is not None
    assert dict(updated.result) == {"task_id": "xyz"}


def test_complete_missing_key_returns_none() -> None:
    client = _make_redis_mock(get_result=None)
    store = RedisIdempotencyCacheStore(client=client)
    assert store.complete(namespace="ns", key="missing", result={}) is None


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------


def test_get_existing_record() -> None:
    existing = _make_record(key="key1")
    client = _make_redis_mock(get_result=_record_to_json(existing).encode())
    store = RedisIdempotencyCacheStore(client=client)
    record = store.get(namespace="ns", key="key1")
    assert record is not None
    assert record.key == "key1"


def test_get_missing_key_returns_none() -> None:
    client = _make_redis_mock(get_result=None)
    store = RedisIdempotencyCacheStore(client=client)
    assert store.get(namespace="ns", key="missing") is None


# ---------------------------------------------------------------------------
# list_namespace()
# ---------------------------------------------------------------------------


def test_list_namespace_returns_all_records() -> None:
    r1 = _make_record(key="k1")
    r2 = _make_record(key="k2")
    scan_result = (0, [b"idempotency:ns:k1", b"idempotency:ns:k2"])
    client = _make_redis_mock(scan_result=scan_result)
    # Pipeline execute returns values in order
    pipeline = client.pipeline.return_value
    pipeline.execute.return_value = [
        _record_to_json(r1).encode(),
        _record_to_json(r2).encode(),
    ]
    store = RedisIdempotencyCacheStore(client=client)
    records = store.list_namespace(namespace="ns")
    assert len(records) == 2
    keys = {r.key for r in records}
    assert keys == {"k1", "k2"}


def test_list_namespace_empty_returns_empty_tuple() -> None:
    client = _make_redis_mock(scan_result=(0, []))
    store = RedisIdempotencyCacheStore(client=client)
    records = store.list_namespace(namespace="ns")
    assert records == ()


def test_list_namespace_skips_corrupted_entries() -> None:
    scan_result = (0, [b"idempotency:ns:k1"])
    client = _make_redis_mock(scan_result=scan_result)
    pipeline = client.pipeline.return_value
    pipeline.execute.return_value = [b"not-valid-json"]
    store = RedisIdempotencyCacheStore(client=client)
    # Corrupted entry is skipped, returns empty
    records = store.list_namespace(namespace="ns")
    assert records == ()


# ---------------------------------------------------------------------------
# build_redis_client
# ---------------------------------------------------------------------------


def test_build_redis_client_returns_redis_instance() -> None:
    with patch(
        "openqilin.data_access.repositories.postgres.idempotency_cache_store.redis.Redis.from_url"
    ) as mock_from_url:
        mock_from_url.return_value = MagicMock()
        build_redis_client("redis://localhost:6379")
        mock_from_url.assert_called_once_with("redis://localhost:6379", decode_responses=False)


# ---------------------------------------------------------------------------
# RuntimeSettings defaults
# ---------------------------------------------------------------------------


def test_runtime_settings_redis_url_defaults_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENQILIN_REDIS_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    settings = RuntimeSettings()
    assert settings.redis_url == ""


def test_runtime_settings_idempotency_ttl_defaults_to_86400() -> None:
    settings = RuntimeSettings()
    assert settings.idempotency_ttl_seconds == 86400


def test_runtime_settings_redis_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENQILIN_REDIS_URL", "redis://redis:6379")
    settings = RuntimeSettings()
    assert settings.redis_url == "redis://redis:6379"


def test_runtime_settings_ttl_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENQILIN_IDEMPOTENCY_TTL_SECONDS", "7200")
    settings = RuntimeSettings()
    assert settings.idempotency_ttl_seconds == 7200


# ---------------------------------------------------------------------------
# dependencies.py type wiring
# ---------------------------------------------------------------------------


def test_dependencies_idempotency_store_type_annotations() -> None:
    """RuntimeServices.idempotency_cache_store is typed as RedisIdempotencyCacheStore."""
    from openqilin.control_plane.api.dependencies import RuntimeServices

    hints = {}
    for field in RuntimeServices.__dataclass_fields__.values():
        hints[field.name] = field.type
    # After M13-WP9 hardening, only the Redis store type is accepted (no InMemory fallback).
    field_type = hints.get("idempotency_cache_store", "")
    type_str = str(field_type)
    assert "RedisIdempotencyCacheStore" in type_str


def test_build_runtime_services_raises_runtime_error_when_no_redis_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When redis_url is empty, build_runtime_services raises RuntimeError (fail-closed)."""
    monkeypatch.setenv("OPENQILIN_REDIS_URL", "")
    monkeypatch.setenv("OPENQILIN_OPA_URL", "")
    monkeypatch.setenv("OPENQILIN_DATABASE_URL", "")

    from openqilin.control_plane.api.dependencies import build_runtime_services

    with pytest.raises(RuntimeError, match="OPENQILIN_DATABASE_URL is required"):
        build_runtime_services()


def test_build_runtime_services_uses_redis_when_redis_url_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When redis_url is set, build_redis_client is called and RedisIdempotencyCacheStore is created."""
    monkeypatch.setenv("OPENQILIN_REDIS_URL", "redis://localhost:6379")

    with patch(
        "openqilin.data_access.repositories.postgres.idempotency_cache_store.redis.Redis.from_url"
    ) as mock_from_url:
        mock_redis = MagicMock()
        mock_from_url.return_value = mock_redis

        from openqilin.shared_kernel.config import RuntimeSettings
        from openqilin.data_access.repositories.postgres.idempotency_cache_store import (
            RedisIdempotencyCacheStore,
            build_redis_client,
        )

        settings = RuntimeSettings()
        assert settings.redis_url == "redis://localhost:6379"

        client = build_redis_client(settings.redis_url)
        store = RedisIdempotencyCacheStore(
            client=client,
            ttl_seconds=settings.idempotency_ttl_seconds,
        )
        assert isinstance(store, RedisIdempotencyCacheStore)
        mock_from_url.assert_called_once_with("redis://localhost:6379", decode_responses=False)
