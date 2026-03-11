# OpenQilin v1 - Implementation Framework Selection

## 1. Scope
- Lock the baseline Python frameworks and libraries for v1 implementation.
- Keep the stack small, async-capable, and aligned with `uv`.

## 2. Selection Principles
- Prefer batteries-included libraries with low integration friction.
- Prefer typed, async-friendly libraries already common in the Python ecosystem.
- Avoid introducing additional runtimes such as Celery unless v1 throughput requires them.

## 3. Selected Baseline
| Concern | Selection | Rationale |
| --- | --- | --- |
| Python packaging and env | `uv` | single tool for sync, lock, run, and reproducibility |
| API framework | `FastAPI` + `uvicorn` | existing design baseline, async, typed request handling |
| settings/config | `pydantic-settings` | typed env parsing, simple integration with Pydantic models |
| schema/validation | `pydantic v2` | shared DTO/request/response validation across apps |
| HTTP client | `httpx` | async-first, timeout support, testable transport layer |
| database access | `SQLAlchemy 2.x` async engine | mature Postgres support and explicit transaction control |
| migration framework | `Alembic` | standard migration tool for SQLAlchemy-managed schemas |
| PostgreSQL driver | `psycopg` | current Postgres driver with solid SQLAlchemy support |
| Redis client | `redis.asyncio` | direct async client, no extra abstraction needed in v1 |
| CLI | `Typer` | clean `admin_cli` UX with low complexity |
| retry/backoff | `tenacity` | bounded retries at adapter boundaries only |
| logging | `structlog` over stdlib logging | consistent structured JSON logs and context propagation |
| test runner | `pytest` | standard baseline |
| async test support | `pytest-asyncio` | async runtime coverage |
| coverage | `pytest-cov` | simple CI coverage reporting |
| HTTP mocking | `respx` | native `httpx` mocking for adapter tests |
| lint + format | `ruff` | one fast tool for lint and formatting |
| type checking | `mypy` | pragmatic static checking for service boundaries |

## 4. Usage Conventions
### 4.1 FastAPI and Pydantic
- FastAPI routers own HTTP transport details only.
- Pydantic request/response models live with the owning module boundary.
- Internal domain services accept typed DTOs, not raw request dicts.

### 4.2 SQLAlchemy
- Use SQLAlchemy 2.x async engine/session.
- Prefer explicit repository/query objects over implicit active-record patterns.
- Use ORM selectively for aggregate persistence and SQLAlchemy Core for read-heavy/query-contract paths.
- Transaction boundaries are owned by application services, not repositories.

### 4.3 Retry Policy
- `tenacity` is allowed only at external adapter boundaries:
  - ACP transport
  - LLM provider calls
  - observability exports where fail-soft is allowed
- Policy and budget decisions are not retried automatically on uncertain outcomes.

### 4.4 Logging and Telemetry
- `structlog` emits JSON logs with `trace_id`, `task_id`, `project_id`, and policy metadata when available.
- OpenTelemetry remains the canonical tracing and metrics path.
- Logging helpers live under `observability`, not in feature modules.

## 5. Packaging and Entrypoints
- `api_app`: FastAPI + `uvicorn`
- `orchestrator_worker`: asyncio worker process started via `uv run python -m ...`
- `communication_worker`: asyncio worker process started via `uv run python -m ...`
- `admin_cli`: Typer-based operational CLI

v1 posture:
- no Celery
- no message broker beyond Redis/PostgreSQL-backed coordination already in design
- no multi-package workspace split

## 6. Dependency Group Conventions
Minimum `pyproject.toml` groups:
- `default`: runtime dependencies
- `dev`: local developer helpers
- `test`: pytest and test-only libraries
- `lint`: ruff, mypy, stub packages
- `ops`: migration/bootstrap/operational helpers when separated from runtime default

## 7. Merge Bar for New Libraries
A new library should not be introduced unless it:
- removes meaningful implementation burden
- has a clear ownership area
- does not overlap an existing selected library
- is captured in this document and `pyproject.toml`

## 8. Related Design Artifacts
- `design/v1/foundation/ImplementationFoundation-v1.md`
- `design/v1/architecture/ImplementationArchitecture-v1.md`
- `implementation/v1/quality/QualityAndDelivery-v1.md`
