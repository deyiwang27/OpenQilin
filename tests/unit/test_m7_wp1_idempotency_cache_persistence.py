from __future__ import annotations

from pathlib import Path

from openqilin.data_access.cache.idempotency_store import InMemoryIdempotencyCacheStore


def test_idempotency_cache_store_persists_records(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "system_root" / "runtime" / "idempotency.json"
    store = InMemoryIdempotencyCacheStore(snapshot_path=snapshot_path)

    status, created = store.claim(
        namespace="communication_delivery",
        key="delivery-key-001",
        payload_hash="hash-001",
    )
    assert status == "new"
    assert created.attempt_count == 0
    attempted = store.increment_attempt(namespace="communication_delivery", key="delivery-key-001")
    assert attempted is not None
    assert attempted.attempt_count == 1
    completed = store.complete(
        namespace="communication_delivery",
        key="delivery-key-001",
        result={"accepted": False, "error_code": "retry_exhausted"},
    )
    assert completed is not None
    assert completed.status == "completed"

    reloaded = InMemoryIdempotencyCacheStore(snapshot_path=snapshot_path)
    restored = reloaded.get(namespace="communication_delivery", key="delivery-key-001")
    assert restored is not None
    assert restored.status == "completed"
    assert restored.attempt_count == 1
    assert dict(restored.result or ())["error_code"] == "retry_exhausted"
