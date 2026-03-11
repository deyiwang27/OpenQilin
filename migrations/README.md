# Migrations

Forward-only database migrations for OpenQilin v1 live here.

Baseline files:
- `alembic.ini` in repository root
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/`

Current contract baseline:
- `20260311_0001_pgvector_baseline_contract.py`
  - enables `pgvector` extension (`CREATE EXTENSION IF NOT EXISTS vector`)
  - creates `knowledge_embedding` extension-dependent baseline table
