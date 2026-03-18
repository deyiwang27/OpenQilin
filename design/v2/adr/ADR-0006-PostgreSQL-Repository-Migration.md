# ADR-0006 — PostgreSQL Repository Migration

**Date:** 2026-03-15
**Status:** Approved
**Author:** Claude (Architect)
**Ratified by:** Owner — approved retroactively on 2026-03-17 (M12 merge)
**Supersedes:** —
**Superseded by:** —

---

## Context

All eight runtime repositories in M11 and earlier were backed by Python dicts (`InMemory*` classes). These served as scaffolding during initial development but had two critical problems:

1. **No persistence across restarts.** Task state, identity mappings, agent registry entries, and audit records were lost on every process restart. This made the system unusable for its intended purpose (long-running autonomous agents).
2. **False test assurance.** Tests running against in-memory stores could not detect bugs that only manifest with real ACID semantics — concurrent writes, row locking for budget, cross-restart recovery. See ADR-0008 for the full analysis.

Bug findings from the architectural review that required PostgreSQL:
- **C-6** (critical): Role was derived from the HTTP header, not from the identity mapping store. The identity store must be real PostgreSQL to be tamper-resistant.
- **C-5** (critical): Audit records must be durable. An in-memory audit log is erased on every restart, violating the immutability requirement.
- **H-4/H-5/H-6**: Three concurrency bugs in the task repository that are only observable under real PostgreSQL semantics.

M12-WP3 wired PostgreSQL for all six primary repositories and Redis for idempotency.

---

## Decision

Replace all `InMemory*` repository classes with Postgres-backed implementations gated on the `OPENQILIN_DATABASE_URL` environment variable.

**Schema:** all tables created via Alembic forward-only migrations. Six migrations shipped in M12-WP3 (tasks, agents, audit_events, identity_channels, projects, governance_artifacts). Two more in M13 (project_space_bindings).

**Gating pattern in `dependencies.py`:**
```python
if not settings.database_url:
    raise RuntimeError(
        "OPENQILIN_DATABASE_URL is required. "
        "Run: docker compose --profile core up -d"
    )
```
This enforces fail-closed startup: the service refuses to start without a real database rather than silently degrading to in-memory mode.

**Repository interface:** each repository implements a Protocol type. `PostgresXxxRepository` classes use SQLAlchemy Core (not ORM) with explicit transaction boundaries. Raw SQL is never written in routers or handlers — only in repository classes under `data_access/repositories/postgres/`.

**Redis for idempotency:** `RedisIdempotencyCacheStore` replaces `InMemoryIdempotencyCacheStore` for ingress deduplication. Gated on `OPENQILIN_REDIS_URL`.

**Bug fixes delivered alongside migration:**
- H-4: `get_runtime_services()` raises `RuntimeError` instead of silently creating a second `RuntimeServices` instance when app state is not pre-initialized.
- H-5: Startup recovery only re-claims `queued`/`dispatched`/`running`/`blocked` tasks; `failed`/`cancelled` tasks no longer permanently block idempotency keys.
- H-6: Terminal status count excludes `dispatched` (only `completed`/`failed`/`cancelled`/`blocked` are terminal).

---

## Rationale

| Option | Reason accepted / rejected |
|---|---|
| **Chosen: PostgreSQL via SQLAlchemy Core + Alembic** | Already in the stack. ACID guarantees required by constitution for audit immutability. Alembic provides the forward-only migration discipline required by governance constraints. |
| Alternative: SQLite (file-backed) | No concurrent write support. Not suitable for a multi-process deployment (control plane + orchestrator worker). |
| Alternative: Keep InMemory + persist to JSON on disk | Not ACID. Concurrency bugs in H-4/H-5/H-6 would remain. Not auditable. |
| Alternative: MongoDB / document store | No ACID transactions. Audit immutability cannot be enforced at the database level. Not aligned with the relational model used by Grafana for dashboard queries. |

---

## Consequences

- **Implementation:** `data_access/repositories/postgres/` — 7 repository files; `migrations/versions/` — 6 Alembic migration files.
- **Tests:** all component and integration tests now require the compose stack (`postgres:5432`, `redis:6379`). Pure-logic unit tests marked `@pytest.mark.no_infra` can still run without compose (see ADR-0008).
- **Governance:** `OPENQILIN_DATABASE_URL` and `OPENQILIN_REDIS_URL` are required in production. Schema changes must go through Alembic — never `CREATE TABLE` in application code. This is a CI merge gate.
- **Compose:** `postgres` and `redis` services required in `compose.yml --profile core`.

---

## References

- Spec: `spec/infrastructure/architecture/RuntimeArchitecture.md`
- Milestone design: `design/v2/architecture/M12-InfrastructureWiringAndSecurityModuleDesign-v2.md`
- Implementing commit: `e8e1a69` — feat(m12-wp3): PostgreSQL repository migration + H-4/H-5/H-6 bug fixes
- GitHub issue: #82 (M12-WP3)
- Related: ADR-0008 (completes InMemory removal from production paths)
