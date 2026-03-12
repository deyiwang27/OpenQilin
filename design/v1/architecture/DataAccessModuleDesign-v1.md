# OpenQilin v1 - Data Access Module Design

## 1. Scope
- Translate the data component design into implementation modules under `src/openqilin/data_access/`.

## 2. Package Layout
```text
src/openqilin/data_access/
  db/
    engine.py
    session.py
    transaction.py
  repositories/
    runtime_state.py
    governance.py
    communication.py
    artifacts.py
    knowledge.py
  read_models/
    project_snapshot.py
    task_runtime_context.py
    artifact_search.py
  outbox/
    writer.py
    consumers.py
    checkpoints.py
  cache/
    redis_keys.py
    cache_store.py
    idempotency_store.py
```

## 3. Repository Rules
- repositories own persistence mapping only
- cross-repository transactions are coordinated by application services
- read models may use SQLAlchemy Core-oriented queries for contract efficiency
- Redis-backed stores are non-authoritative helpers only

MVP v1 data posture additions:
- relational DB is authoritative for project lifecycle and control metadata.
- rich-text project documents are file-backed under `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/`.
- repositories must persist file pointer/hash metadata and fail closed on mismatch.

## 4. Key Interfaces
- `UnitOfWork.begin()`
- `RuntimeStateRepository.save_task(...)`
- `GovernanceRepository.append_policy_decision(...)`
- `OutboxWriter.append(event)`
- `CheckpointStore.advance(consumer_name, checkpoint)`
- `ArtifactSearchReadModel.search(project_id, query, filters)`
- `ProjectArtifactRepository.create_or_update_with_hash(...)`
- `ProjectDocumentPolicyRepository.validate_type_and_cap(...)`

## 5. Testing Focus
- transaction boundary correctness
- outbox append and replay idempotency
- Redis key derivation and TTL behavior
- query-contract read model correctness and project isolation
