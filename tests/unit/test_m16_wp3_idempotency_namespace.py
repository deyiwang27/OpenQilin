"""Unit tests for M16-WP3: Redis idempotency namespace separation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

from openqilin.data_access.cache.idempotency_store import CacheIdempotencyRecord
from openqilin.data_access.repositories.postgres.idempotency_cache_store import (
    RedisIdempotencyCacheStore,
    _record_to_json,
)


def _make_redis_mock(
    *,
    set_result: Any = True,
    get_result: bytes | None = None,
) -> MagicMock:
    client = MagicMock()
    client.set.return_value = set_result
    client.get.return_value = get_result
    return client


def _make_record(
    *,
    namespace: str = "ingress",
    key: str = "abc",
    payload_hash: str = "h1",
    status: str = "in_progress",
) -> CacheIdempotencyRecord:
    now = datetime.now(tz=UTC)
    return CacheIdempotencyRecord(
        namespace=namespace,
        key=key,
        payload_hash=payload_hash,
        status=status,  # type: ignore[arg-type]
        attempt_count=0,
        result=None,
        created_at=now,
        updated_at=now,
    )


def test_namespace_bound_at_init_used_in_redis_key() -> None:
    client = _make_redis_mock(set_result=True)
    store = RedisIdempotencyCacheStore(client=client, namespace="ingress")

    status, _ = store.claim(key="abc", payload_hash="h1")

    assert status == "new"
    assert client.set.call_args.args[0] == "idempotency:ingress:abc"


def test_cross_namespace_no_collision() -> None:
    client = _make_redis_mock(set_result=True)
    ingress_store = RedisIdempotencyCacheStore(client=client, namespace="ingress")
    communication_store = RedisIdempotencyCacheStore(client=client, namespace="communication")

    ingress_status, _ = ingress_store.claim(key="abc", payload_hash="h1")
    communication_status, _ = communication_store.claim(key="abc", payload_hash="h1")

    assert ingress_status == "new"
    assert communication_status == "new"
    set_keys = {call.args[0] for call in client.set.call_args_list}
    assert "idempotency:ingress:abc" in set_keys
    assert "idempotency:communication:abc" in set_keys


def test_within_namespace_deduplication_still_works() -> None:
    in_progress_record = _make_record(namespace="ingress", key="abc", payload_hash="h1")
    client = _make_redis_mock(get_result=_record_to_json(in_progress_record).encode())
    client.set.side_effect = [True, None]
    store = RedisIdempotencyCacheStore(client=client, namespace="ingress")

    first_status, _ = store.claim(key="abc", payload_hash="h1")
    second_status, _ = store.claim(key="abc", payload_hash="h1")

    assert first_status == "new"
    assert second_status == "in_progress"


def test_namespace_attrs_are_separate() -> None:
    client = _make_redis_mock()
    store_a = RedisIdempotencyCacheStore(client=client, namespace="ingress")
    store_b = RedisIdempotencyCacheStore(client=client, namespace="communication")

    assert store_a._namespace == "ingress"  # noqa: SLF001
    assert store_b._namespace == "communication"  # noqa: SLF001
    assert store_a._key("x") == "idempotency:ingress:x"  # noqa: SLF001
    assert store_b._key("x") == "idempotency:communication:x"  # noqa: SLF001
